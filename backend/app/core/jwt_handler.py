from datetime import datetime, timezone

from jose import JWTError, jwt

from app.core.security import (
    ALGORITHM,
    SECRET_KEY,
    get_access_token_expiry,
)


def create_access_token(data: dict) -> str:
    """
    Create a signed JWT access token.
    """

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + get_access_token_expiry()

    to_encode.update(
        {
            "exp": expire,
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


def verify_access_token(token: str) -> dict:
    """
    Verify a JWT access token and return its payload.
    """

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        return payload

    except JWTError as exc:
        raise ValueError("Invalid or expired token.") from exc


def decode_expired_token(token: str) -> dict:
    """
    Decode a JWT access token ignoring expiration to extract payload claims for silent renewal.
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
        return payload
    except JWTError as exc:
        raise ValueError("Invalid token structure.") from exc

