import os
import secrets
from datetime import timedelta
from typing import cast

from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

# ------------------------------------------------------------------
# JWT Configuration
# ------------------------------------------------------------------

SECRET_KEY = cast(str, os.getenv("JWT_SECRET_KEY"))
ALGORITHM = cast(str, os.getenv("JWT_ALGORITHM", "HS256"))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))

# ------------------------------------------------------------------
# Password Hashing
# ------------------------------------------------------------------

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """
    Hashes a plain-text password.
    """
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verifies a plain-text password against its hash.
    """
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


# ------------------------------------------------------------------
# Access Token Expiry
# ------------------------------------------------------------------


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
