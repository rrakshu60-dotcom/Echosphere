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
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_announcements_status ON announcements(status);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_announcements_status_created_at ON announcements(status, created_at);"))
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
    from app.seeders.announcement import seed_announcements

    with SessionLocal() as db_session:
        from app.models.user import User
        from app.models.announcement import Announcement
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
        if db_session.query(Announcement).count() == 0:
            seed_announcements(db_session)
        seed_default_speaker_nodes_if_empty(db_session)
except Exception:
    pass

import threading
import time
from contextlib import asynccontextmanager


def _speaker_and_repeat_daemon():
    """
    High-precision background daemon:
    - Runs every 3 seconds: Auto-advances speaker queue (progresses playing items after duration,
      triggers queued notices when scheduled_time <= now, and dispatches to hardware nodes).
    - Runs every 45 seconds: Evaluates campus break slot repeat announcement schedules.
    """
    from app.db.database import SessionLocal
    from app.services.hardware_speaker_service import auto_advance_speaker_queue
    from app.services.repeat_schedule_service import evaluate_and_dispatch_repeat_slots

    tick_count = 0
    while True:
        try:
            time.sleep(3)
            tick_count += 1
            with SessionLocal() as db_session:
                # 1. Real-time speaker queue progression & scheduled time triggers (every 3s)
                auto_advance_speaker_queue(db_session)

                # 2. Campus acoustic window repeat schedules (every ~45s = 15 ticks)
                if tick_count % 15 == 0:
                    evaluate_and_dispatch_repeat_slots(db_session)
        except Exception:
            time.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=_speaker_and_repeat_daemon, daemon=True, name="SpeakerAndRepeatDaemon")
    t.start()
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




# -------------------------
# Health Check
# -------------------------


@app.get("/")
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
