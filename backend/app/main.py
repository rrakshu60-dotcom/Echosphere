import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
            conn.commit()
except Exception as exc:
    print(f"Startup migration note: {exc}")

# Seed default database entities if table is empty
try:
    from app.db.database import SessionLocal
    from app.models.role import Role
    from app.repositories.hardware_repository import seed_default_speaker_nodes_if_empty
    from app.seeders.role import seed_roles
    from app.seeders.department import seed_departments
    from app.seeders.category import seed_categories
    from app.seeders.delivery_type import seed_delivery_types
    from app.seeders.user import seed_users

    with SessionLocal() as db_session:
        if db_session.query(Role).count() == 0:
            seed_roles(db_session)
            seed_departments(db_session)
            seed_categories(db_session)
            seed_delivery_types(db_session)
            seed_users(db_session)
        seed_default_speaker_nodes_if_empty(db_session)
except Exception:
    pass

app = FastAPI(
    title="EchoSphere Backend",
    version="1.0.0",
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
    _rate_limit_exceeded_handler,
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
