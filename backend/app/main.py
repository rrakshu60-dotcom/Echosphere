from typing import Any, cast
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.ai import router as ai_router
from app.api.v1.announcement import router as announcement_router
from app.api.v1.audit_log import router as audit_log_router
from app.api.v1.auth import router as auth_router
from app.api.v1.hardware import router as hardware_router
from app.api.v1.notification import router as notification_router
from app.api.v1.password_reset import router as password_reset_router
from app.api.v1.user_management import router as user_management_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.repeat_schedule import router as repeat_schedule_router
from app.api.v1.vip_protocol import router as vip_protocol_router
import app.models
from app.models.speaker_command import SpeakerCommand
from app.core.rate_limiter import limiter
from app.db.database import Base, engine
from app.db.database import SessionLocal as _QueueSessionFactory
from app.core.queue_signal import install_session_hooks

# Wake the speaker queue daemon instantly on any queue / schedule / announcement commit
install_session_hooks(_QueueSessionFactory)

Base.metadata.create_all(bind=engine)
SpeakerCommand.__table__.create(bind=engine, checkfirst=True)

# Safe Schema Migration Check (Supports both PostgreSQL & SQLite)
try:
    with engine.connect() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE announcements ADD COLUMN IF NOT EXISTS target_audience VARCHAR(255) DEFAULT 'Entire College';"))
            conn.execute(text("ALTER TABLE announcements ADD COLUMN IF NOT EXISTS ai_summary TEXT;"))
            conn.execute(text("ALTER TABLE announcements ADD COLUMN IF NOT EXISTS speaker_voice VARCHAR(20) DEFAULT 'female';"))
            conn.execute(text("ALTER TABLE speaker_queue ADD COLUMN IF NOT EXISTS speaker_node_id INTEGER;"))
            conn.execute(text("ALTER TABLE speaker_queue ADD COLUMN IF NOT EXISTS speaker_confirmed_at TIMESTAMP WITHOUT TIME ZONE;"))
            conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN IF NOT EXISTS repeat_mode VARCHAR(20) DEFAULT 'INTERVAL';"))
            conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN IF NOT EXISTS interval_minutes INTEGER DEFAULT 15;"))
            conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN IF NOT EXISTS max_repeats INTEGER DEFAULT 3;"))
            conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN IF NOT EXISTS play_on_publish BOOLEAN DEFAULT TRUE;"))
            conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN IF NOT EXISTS next_repeat_at TIMESTAMP WITHOUT TIME ZONE;"))
            conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN IF NOT EXISTS last_repeat_at TIMESTAMP WITHOUT TIME ZONE;"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_announcements_status ON announcements(status);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_announcements_status_created_at ON announcements(status, created_at);"))
            conn.commit()
        else:
            res = conn.execute(text("PRAGMA table_info(announcements);")).fetchall()
            col_names = [r[1] for r in res]
            if "target_audience" not in col_names:
                conn.execute(text("ALTER TABLE announcements ADD COLUMN target_audience VARCHAR(255) DEFAULT 'Entire College';"))
            if "ai_summary" not in col_names:
                conn.execute(text("ALTER TABLE announcements ADD COLUMN ai_summary TEXT;"))
            if "speaker_voice" not in col_names:
                conn.execute(text("ALTER TABLE announcements ADD COLUMN speaker_voice VARCHAR(20) DEFAULT 'female';"))
            sq_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(speaker_queue);")).fetchall()]
            if sq_cols and "speaker_confirmed_at" not in sq_cols:
                conn.execute(text("ALTER TABLE speaker_queue ADD COLUMN speaker_confirmed_at DATETIME;"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_announcements_status ON announcements(status);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_announcements_status_created_at ON announcements(status, created_at);"))

            # Repeat schedules table migration for SQLite
            try:
                sched_res = conn.execute(text("PRAGMA table_info(announcement_repeat_schedules);")).fetchall()
                sched_cols = [r[1] for r in sched_res]
                if "repeat_mode" not in sched_cols:
                    conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN repeat_mode VARCHAR(20) DEFAULT 'INTERVAL';"))
                if "interval_minutes" not in sched_cols:
                    conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN interval_minutes INTEGER DEFAULT 15;"))
                if "max_repeats" not in sched_cols:
                    conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN max_repeats INTEGER DEFAULT 3;"))
                if "play_on_publish" not in sched_cols:
                    conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN play_on_publish BOOLEAN DEFAULT 1;"))
                if "next_repeat_at" not in sched_cols:
                    conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN next_repeat_at DATETIME;"))
                if "last_repeat_at" not in sched_cols:
                    conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN last_repeat_at DATETIME;"))
            except Exception:
                pass
            conn.commit()
except Exception as exc:
    print(f"Startup migration note: {exc}")

# Seed default database entities if table is empty
try:
    from app.db.database import SessionLocal
    from app.models.role import Role
    from app.models.department import Department
    from app.models.announcement_category import AnnouncementCategory
    from app.models.delivery_type import DeliveryType
    from app.repositories.hardware_repository import seed_default_speaker_nodes_if_empty
    from app.seeders.role import seed_roles
    from app.seeders.department import seed_departments
    from app.seeders.category import seed_categories
    from app.seeders.delivery_type import seed_delivery_types
    from app.seeders.user import seed_users

    with SessionLocal() as db_session:
        from app.models.user import User
        if db_session.query(Role).count() == 0:
            seed_roles(db_session)
        if db_session.query(Department).count() == 0:
            seed_departments(db_session)
        if db_session.query(AnnouncementCategory).count() == 0:
            seed_categories(db_session)
        if db_session.query(DeliveryType).count() == 0:
            seed_delivery_types(db_session)
        if db_session.query(User).count() == 0:
            seed_users(db_session)
        seed_default_speaker_nodes_if_empty(db_session)
except Exception:
    pass

import threading
import time
from contextlib import asynccontextmanager


def _speaker_and_repeat_daemon():
    """
    Event-driven, zero-lag speaker queue & repeat schedule engine.

    Every pass runs BOTH the speaker queue progression and the repeat schedule
    evaluation. Between passes the daemon does not sleep on a fixed timer; it waits
    on app.core.queue_signal and wakes:
      - instantly when any request commits a queue / repeat schedule / announcement change
        (publish, approve, emergency override, ESP32 'complete', schedule edits, ...), or
      - exactly when the next known event is due (current notice ends, a scheduled notice
        or repeat round comes due, or an IST break / custom window opens or closes).
    After a pass that changed something it re-runs immediately so chained transitions
    (notice finishes -> next starts -> repeat enqueued) happen back-to-back.
    """
    from app.db.database import SessionLocal
    from app.services.hardware_speaker_service import (
        auto_advance_speaker_queue,
        get_next_queue_wake_seconds,
    )
    from app.services.repeat_schedule_service import evaluate_and_dispatch_repeat_slots
    from app.core.queue_signal import DAEMON_SESSION_FLAG, wait_for_queue_change

    # Upper bound on sleep, only as a safety net for changes made outside this process
    # (e.g. maintenance scripts writing directly to Supabase). In-process changes wake instantly.
    safety_poll = float(os.getenv("QUEUE_DAEMON_SAFETY_POLL_SEC", "1.0"))
    max_chained_passes = 8

    while True:
        wait_seconds = safety_poll
        try:
            for _ in range(max_chained_passes):
                with SessionLocal() as db_session:
                    db_session.info[DAEMON_SESSION_FLAG] = True
                    advance_res = auto_advance_speaker_queue(db_session)
                    repeat_res = evaluate_and_dispatch_repeat_slots(db_session)
                    changed = bool(advance_res) or bool((repeat_res or {}).get("dispatched"))
                    if not changed:
                        wait_seconds = get_next_queue_wake_seconds(db_session, max_wait=safety_poll)
                        break
        except Exception as exc:
            print(f"Speaker queue daemon note: {exc}")
            wait_seconds = 1.0
        wait_for_queue_change(wait_seconds)


def _prewarm_recent_announcements():
    """
    On server boot, pre-warms top recent published announcements into Render's ephemeral disk
    so hardware speaker nodes and web audio player experience zero latency (<0.2s) from the very first request.
    """
    try:
        time.sleep(4)
        from app.db.database import SessionLocal
        from app.models.announcement import Announcement
        from app.core.enums.announcement import AnnouncementStatus
        from app.services.tts_service import generate_announcement_audio_sync
        from app.api.v1.announcement import _find_cached_audio_file
        with SessionLocal() as db_session:
            recent = (
                db_session.query(Announcement)
                .filter(Announcement.status == AnnouncementStatus.PUBLISHED)
                .order_by(Announcement.id.desc())
                .limit(5)
                .all()
            )
            for a in recent:
                v = getattr(a, "speaker_voice", "female") or "female"
                clean_v = str(v).lower()
                tag = f"american_{clean_v}"
                fname, fpath, _ = _find_cached_audio_file(a.id, tag, include_chime=False, prefer_wav=True)
                if not fname or not fpath:
                    try:
                        generate_announcement_audio_sync(
                            a.id,
                            f"{a.title}. {a.description}",
                            gender=clean_v,
                            include_chime=False,
                        )
                    except Exception:
                        pass
    except Exception as exc:
        print(f"Startup audio pre-warm note: {exc}")


def _render_self_keepalive():
    """
    Render's free tier sleeps after 15 minutes without inbound traffic, and the GitHub cron
    keep-alive is throttled to a few runs a day. While the service is up, ping our own public
    URL every 9 minutes during campus hours (07:00-23:30 IST) so it never dozes off mid-day.
    It cannot wake a sleeping service; the speaker's heartbeats and an external monitor do that.
    """
    import urllib.request
    from datetime import datetime, timedelta, timezone

    url = (os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")
    if not url:
        return  # not running on Render
    while True:
        time.sleep(540)
        ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        minutes = ist.hour * 60 + ist.minute
        if 7 * 60 <= minutes <= 23 * 60 + 30:
            try:
                urllib.request.urlopen(url + "/", timeout=20).read(64)
            except Exception as exc:
                print(f"Render self keep-alive note: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=_speaker_and_repeat_daemon, daemon=True, name="SpeakerAndRepeatDaemon")
    t.start()
    t2 = threading.Thread(target=_prewarm_recent_announcements, daemon=True, name="AudioPrewarmDaemon")
    t2.start()
    threading.Thread(target=_render_self_keepalive, daemon=True, name="RenderSelfKeepAlive").start()
    try:
        from app.services.tts_service import start_zerogpu_keepalive_daemon
        start_zerogpu_keepalive_daemon()
    except Exception as exc:
        print(f"ZeroGPU keep-alive startup note: {exc}")
    yield


app = FastAPI(
    title="EchoSphere Backend",
    version="1.1.0",
    lifespan=lifespan,
)


# -------------------------
# CORS Middleware
# -------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=500,
)

# -------------------------
# Static Files (Audio Streams)
# -------------------------

static_audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
try:
    os.makedirs(os.path.join(static_audio_path, "audio_streams"), exist_ok=True)
    if os.path.exists(static_audio_path):
        app.mount("/static", StaticFiles(directory=static_audio_path), name="static")
except Exception as e:
    pass

# -------------------------
# Rate Limiter
# -------------------------

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    cast(Any, _rate_limit_exceeded_handler),
)

# -------------------------
# Register API Routers
# -------------------------

app.include_router(
    auth_router,
    prefix="/api/v1",
)

app.include_router(
    announcement_router,
    prefix="/api/v1",
)

app.include_router(
    hardware_router,
    prefix="/api/v1",
)

app.include_router(
    password_reset_router,
    prefix="/api/v1",
)

app.include_router(
    audit_log_router,
    prefix="/api/v1",
)

app.include_router(
    ai_router,
    prefix="/api/v1",
)

app.include_router(
    notification_router,
    prefix="/api/v1",
)

app.include_router(
    user_management_router,
    prefix="/api/v1",
)

app.include_router(
    websocket_router,
    prefix="/api/v1",
)

app.include_router(
    websocket_router,
)

app.include_router(
    repeat_schedule_router,
    prefix="/api/v1",
)

app.include_router(
    vip_protocol_router,
    prefix="/api/v1",
)




from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# -------------------------
# Health Check & Diagnostics
# -------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    return JSONResponse(
        status_code=500,
        content={
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "traceback": traceback.format_exc().splitlines()[-12:],
        },
    )


@app.get("/api/v1/diagnostic/tts")
def diagnostic_tts(run_test: bool = False, reset_client: bool = False):
    import traceback
    diag = {}
    from app.services.tts_service import (
        STATIC_AUDIO_DIR,
        generate_announcement_audio_sync,
    )
    diag["static_audio_dir"] = STATIC_AUDIO_DIR
    diag["dir_exists"] = os.path.exists(STATIC_AUDIO_DIR)
    diag["kokoro_api_url_configured"] = bool(os.getenv("KOKORO_API_URL"))
    diag["is_render"] = bool(os.getenv("RENDER") or os.getenv("IS_RENDER"))
    diag["local_kokoro_allowed_on_render"] = os.getenv("ENABLE_LOCAL_KOKORO_ON_RENDER", "false").lower() == "true"
    try:
        from app.services.tts_service import get_zerogpu_health_status
        diag["zerogpu_worker"] = get_zerogpu_health_status()
    except Exception:
        pass

    from app.services.tts_service import TTS_ENGINE, KOKORO_API_URL
    diag["TTS_ENGINE"] = TTS_ENGINE
    diag["KOKORO_API_URL"] = KOKORO_API_URL
    diag["ENABLE_REMOTE_KOKORO"] = os.getenv("ENABLE_REMOTE_KOKORO", "true")

    try:
        from app.services.tts_service import prewarm_gradio_client, _cached_gradio_client
        if reset_client or _cached_gradio_client is None:
            prewarm_gradio_client(force=True)
        from app.services.tts_service import _cached_gradio_client as _chk_client
        diag["gradio_client_status"] = "INITIALIZED" if _chk_client is not None else "NONE"
        if _chk_client is not None and not run_test:
            t0 = time.time()
            pred_res = _chk_client.predict("Test Kokoro synthesis", "af_heart", 1.0, api_name="/synthesize")
            diag["direct_predict"] = {
                "success": True,
                "elapsed_sec": round(time.time() - t0, 2),
                "result": str(pred_res),
            }
    except Exception as gce:
        import app.services.tts_service as tts_mod
        tts_mod._cached_gradio_client = None
        diag["gradio_client_status"] = f"ERROR: {gce}"
        diag["gradio_client_traceback"] = traceback.format_exc().splitlines()[-6:]

    if run_test:
        try:
            test_id = int(time.time() % 100000)
            res = generate_announcement_audio_sync(
                announcement_id=test_id,
                text="EchoSphere diagnostic audio test.",
                gender="female",
                accent="american",
                include_chime=False,
            )
            diag["generate_result"] = res
        except Exception as e:
            diag["generate_error"] = f"{type(e).__name__}: {str(e)}"
            diag["generate_traceback"] = traceback.format_exc().splitlines()[-12:]

    return diag


# HEAD too: uptime monitors (UptimeRobot) probe with HEAD and got 405 "Method Not Allowed"
@app.api_route("/", methods=["GET", "HEAD"])
def root():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "message": "Welcome to EchoSphere Backend",
            "database": "Connected Successfully",
        }

    except Exception as e:
        return {
            "message": "Database Connection Failed",
            "error": str(e),
        }
