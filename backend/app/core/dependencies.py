from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.jwt_handler import verify_access_token
from app.db.database import get_db
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.user_repository import get_user_by_email
from app.services.session_service import session_for_request

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def _resolve_session(token: str, db: Session):
    """
    (user, session) for a bearer token, or None. The token must name a session that is still open
    and belong to an active account, so sign-out, an admin ending the session, a password change
    or disabling the account take effect on the next request.
    """
    try:
        payload = verify_access_token(token)
    except ValueError:
        return None
    session = session_for_request(db, payload.get("sid"))
    if session is None:
        return None
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        return None
    return user, session


def _require_session(token: str, db: Session):
    resolved = _resolve_session(token, db)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has ended. Please sign in again.",
        )
    return resolved


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    return _require_session(token, db)[0]


def get_current_session(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserSession:
    return _require_session(token, db)[1]


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[User]:
    resolved = _resolve_session(token, db) if token else None
    return resolved[0] if resolved else None


def get_optional_current_session(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[UserSession]:
    resolved = _resolve_session(token, db) if token else None
    return resolved[1] if resolved else None


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
