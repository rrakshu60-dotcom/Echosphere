from typing import cast

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.password import verify_password
from app.models.user import User
from app.services.audit_log_service import create_audit_log_service


class SignInRefused(ValueError):
    """A refused sign-in. `reason` goes to the sign-in log; the message is what the user sees."""

    def __init__(self, reason: str, message: str = "Invalid credentials.", user: User | None = None):
        super().__init__(message)
        self.reason = reason
        self.user = user


def check_credentials(
    db: Session,
    identifier: str,
    password: str,
    employee_id: str | None = None,
) -> User:
    """
    Check credentials by USN, Username, Official Email, or Employee ID (exact match) and return the user.
    Raises SignInRefused. Unknown user and wrong password show the same message so accounts can't be probed.
    """
    cleaned = identifier.strip()
    user = (
        db.query(User)
        .filter(
            or_(
                func.lower(User.usn) == cleaned.lower(),
                func.lower(User.official_email) == cleaned.lower(),
                func.lower(User.username) == cleaned.lower(),
                func.lower(User.employee_id) == cleaned.lower(),
            )
        )
        .first()
    )

    if user is None:
        raise SignInRefused("unknown_user")

    if not verify_password(password, cast(str, user.password_hash)):
        raise SignInRefused("wrong_password", user=user)

    if employee_id and user.employee_id:
        if user.employee_id.strip() != employee_id.strip():
            raise SignInRefused("employee_id_mismatch", "Employee ID verification failed.", user=user)

    if not user.is_active:
        raise SignInRefused("disabled", "This account is disabled. Contact the administrator.", user=user)

    return user


def authenticate_user(
    db: Session,
    identifier: str,
    password: str,
    employee_id: str | None = None,
) -> User:
    """Sign-in check: `check_credentials` plus the LOGIN activity entry."""
    user = check_credentials(db, identifier, password, employee_id)
    role_name = user.role.name if user.role else "Student"
    create_audit_log_service(
        db=db,
        user_id=cast(int, user.id),
        action="LOGIN",
        entity="USER",
        entity_id=cast(int, user.id),
        description=f"User {user.full_name} ({role_name}) logged in successfully.",
    )

    return user
