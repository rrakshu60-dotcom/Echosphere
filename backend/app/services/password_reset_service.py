from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    generate_password_reset_token,
    hash_password,
)
from app.models.password_reset_token import PasswordResetToken
from app.repositories.password_reset_repository import (
    create_password_reset_token,
    delete_expired_tokens,
    get_password_reset_token,
    update_password_reset_token,
)
from app.repositories.user_repository import (
    get_user_by_identifier,
    update_user,
)
from app.services.audit_log_service import create_audit_log_service
from app.services.email_service import send_password_reset_email


def forgot_password_service(
    db: Session,
    identifier: str,
):
    """
    Handles forgot password requests.
    """

    user = get_user_by_identifier(
        db,
        identifier,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with the provided Employee ID or Official Email.",
        )

    if user.role.name.lower() == "student":
        return {
            "message": (
                "Student accounts cannot reset passwords directly. "
                "Please contact a Faculty, HoD, Principal, "
                "College Admin, or Developer."
            ),
            "student": True,
        }

    delete_expired_tokens(
        db,
        user.id,
    )

    token = generate_password_reset_token()

    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    )

    create_password_reset_token(
        db,
        reset_token,
    )

    # Replace this with your frontend deep-link later.
    reset_link = f"http://localhost:8000/reset-password?token={token}"

    try:
        send_password_reset_email(
            recipient_email=user.official_email,
            reset_link=reset_link,
        )
    except Exception as exc:
        import logging
        import os
        logging.getLogger(__name__).warning("Password reset email dispatch error: %s. Dev Reset Link: %s", exc, reset_link)
        if not os.getenv("SMTP_SERVER") or os.getenv("ENVIRONMENT", "dev").lower() in ("dev", "development", "local", "test"):
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to send the password reset email. Please try again later.",
            ) from exc

    create_audit_log_service(
        db=db,
        user_id=user.id,
        action="FORGOT_PASSWORD",
        entity="USER",
        entity_id=user.id,
        description="Password reset requested.",
    )

    return {
        "message": "Password reset link has been sent to your registered email.",
        "student": False,
    }


def verify_reset_token_service(
    db: Session,
    token: str,
):
    """
    Verifies whether a password reset token is valid.
    """

    reset_token = get_password_reset_token(
        db=db,
        token=token,
    )

    if reset_token is None:
        return {
            "valid": False,
            "message": "Invalid password reset token.",
        }

    if reset_token.used:
        return {
            "valid": False,
            "message": "This password reset link has already been used.",
        }

    if reset_token.expires_at < datetime.utcnow():
        return {
            "valid": False,
            "message": "Password reset link has expired.",
        }

    return {
        "valid": True,
        "message": "Password reset token is valid.",
    }


def reset_password_service(
    db: Session,
    token: str,
    new_password: str,
):
    """
    Resets a user's password using a valid reset token.
    """

    reset_token = get_password_reset_token(
        db=db,
        token=token,
    )

    if reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token.",
        )

    if reset_token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has already been used.",
        )

    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link has expired.",
        )

    user = reset_token.user

    user.password_hash = hash_password(
        new_password,
    )

    update_user(
        db=db,
        user=user,
    )

    reset_token.used = True

    update_password_reset_token(
        db=db,
        reset_token=reset_token,
    )

    create_audit_log_service(
        db=db,
        user_id=user.id,
        action="RESET_PASSWORD",
        entity="USER",
        entity_id=user.id,
        description="Password reset completed successfully.",
    )

    return {
        "message": "Password has been reset successfully.",
    }
