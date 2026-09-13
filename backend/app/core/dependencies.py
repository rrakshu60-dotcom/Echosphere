from typing import Callable, Optional
from sqlalchemy import or_

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.jwt_handler import verify_access_token
from app.db.database import get_db
from app.models.user import User
from app.repositories.user_repository import get_user_by_email

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def _find_user_by_sub(db: Session, sub: str) -> Optional[User]:
    return (
        db.query(User)
        .filter(
            or_(
                User.official_email == sub,
                User.usn == sub,
                User.username == sub,
                User.employee_id == sub,
            )
        )
        .first()
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = verify_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    sub = payload.get("sub")

    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = _find_user_by_sub(db, str(sub))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    try:
        payload = verify_access_token(token)
        sub = payload.get("sub")
        if sub:
            return _find_user_by_sub(db, str(sub))
    except Exception:
        pass
    return None


def require_roles(*allowed_roles) -> Callable:
    # Flatten arguments if passed as a list or tuple
    flat_roles = set()
    for role in allowed_roles:
        if isinstance(role, (list, tuple, set)):
            for r in role:
                flat_roles.add(str(r))
        else:
            flat_roles.add(str(role))

    # Support aliases for backward compatibility
    expanded_roles = set(flat_roles)
    if "Developer" in flat_roles or "Dev Admin" in flat_roles:
        expanded_roles.add("Dev Admin")
        expanded_roles.add("Developer")
    if "Admin" in flat_roles or "College Admin" in flat_roles:
        expanded_roles.add("College Admin")
        expanded_roles.add("Admin")

    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated.",
            )
        user_role = current_user.role.name if current_user.role else "Student"
        if user_role not in expanded_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return role_checker
