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
from app.core.rate_limiter import limiter
from app.db.database import Base, engine
import app.models  # Ensure all SQLAlchemy models are registered

Base.metadata.create_all(bind=engine)

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
os.makedirs(os.path.join(static_audio_path, "audio_streams"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_audio_path), name="static")

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
