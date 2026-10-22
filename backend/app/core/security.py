import os
import secrets
from datetime import timedelta
from typing import cast

from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------------
# JWT Configuration
# ------------------------------------------------------------------

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or ""
if not SECRET_KEY:
    # Never fall back to a fixed key: anyone could forge tokens with it.
    # A per-process random key keeps local dev working (sessions end on restart).
    SECRET_KEY = secrets.token_urlsafe(48)
    print("WARNING: JWT_SECRET_KEY is not set; using a temporary random key. Set it in the environment.")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# ------------------------------------------------------------------
# Password Hashing
# ------------------------------------------------------------------

# One hasher for the whole app (app.core.password, plain bcrypt). passlib's bcrypt wrapper
# fails with current bcrypt releases, which broke password reset.
from app.core.password import hash_password, verify_password  # noqa: E402,F401


def get_access_token_expiry() -> timedelta:
    """
    Returns the access token expiry duration.
    """
    return timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)


# ------------------------------------------------------------------
# Password Reset Token
# ------------------------------------------------------------------


def generate_password_reset_token() -> str:
    """
    Generates a secure password reset token.
    """
    return secrets.token_urlsafe(32)
