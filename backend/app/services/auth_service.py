from typing import Tuple, cast
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.jwt_handler import create_access_token
from app.core.password import verify_password
from app.models.user import User
from app.services.audit_log_service import create_audit_log_service


def authenticate_user(
    db: Session,
    identifier: str,
    password: str,
    employee_id: str | None = None,
) -> Tuple[str, User]:
    """
    Authenticate a user by USN, Username, Official Email, or Employee ID.
    Returns (access_token, user).
    """
    cleaned = identifier.strip()
    user = (
        db.query(User)
        .filter(
            or_(
                User.usn == cleaned,
                User.official_email == cleaned,
                User.username == cleaned,
                User.employee_id == cleaned,
            )
        )
        .first()
    )

    if user is None:
        raise ValueError("Invalid credentials.")

    role_name = user.role.name if user.role else "Student"

    # College Admin and Dev Admin accounts cannot log in using email according to schema rules
    if role_name in ["College Admin", "Dev Admin", "Developer"]:
        if "@" in cleaned or (user.official_email and user.official_email.lower() == cleaned.lower()):
            raise ValueError("Email login disabled for administrative accounts. Please log in using your Username or Employee ID.")

    if not verify_password(password, cast(str, user.password_hash)):
        raise ValueError("Invalid credentials.")

    if employee_id and user.employee_id:
        if user.employee_id.strip() != employee_id.strip():
            raise ValueError("Employee ID verification failed.")

    role_name = user.role.name if user.role else "Student"

    access_token = create_access_token(
        {
            "sub": user.official_email or user.usn or user.username,
            "role": role_name,
            "user_id": user.id,
        }
    )

    create_audit_log_service(
        db=db,
        user_id=cast(int, user.id),
        action="LOGIN",
        entity="USER",
        entity_id=cast(int, user.id),
        description=f"User {user.full_name} ({role_name}) logged in successfully.",
    )

    return access_token, user

