from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.rate_limiter import limiter
from app.core.dependencies import (
    get_current_session,
    get_current_user,
    get_optional_current_session,
    get_optional_current_user,
    require_roles,
)
from app.db.database import get_db
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import SignInRefused, authenticate_user, check_credentials
from app.services.session_service import (
    client_ip,
    client_user_agent,
    create_session,
    end_all_user_sessions,
    end_session,
    log_app_access,
    log_sign_in,
    refresh_session,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _to_token_response(access_token: str, user: User, refresh_token: str, session: UserSession) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        session_id=int(getattr(session, "id")),
        role=user.role.name if user.role else "Student",
        user_id=int(getattr(user, "id")),
        full_name=str(getattr(user, "full_name", "") or ""),
        official_email=str(user.official_email) if getattr(user, "official_email", None) else None,
        usn=str(user.usn) if getattr(user, "usn", None) else None,
        employee_id=str(user.employee_id) if getattr(user, "employee_id", None) else None,
        department_id=int(user.department_id) if getattr(user, "department_id", None) else None,
    )


def _sign_in(
    db: Session,
    http: Request,
    identifier: str,
    password: str,
    employee_id: Optional[str] = None,
    remember_me: bool = False,
    platform: Optional[str] = None,
) -> TokenResponse:
    ip, ua = client_ip(http), client_user_agent(http)
    try:
        user = authenticate_user(db=db, identifier=identifier, password=password, employee_id=employee_id)
    except SignInRefused as refused:
        log_sign_in(db, identifier, False, refused.reason, ip, ua, platform, user=refused.user)
        raise HTTPException(status_code=400, detail=str(refused))

    access_token, refresh_token, session = create_session(
        db, user, remember_me=remember_me, ip=ip, user_agent=ua, platform=platform
    )
    log_sign_in(db, identifier, True, "ok", ip, ua, platform, user=user, session=session)
    return _to_token_response(access_token, user, refresh_token, session)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
    http: Request,
    db: Session = Depends(get_db),
):
    return _sign_in(
        db,
        http,
        request.identifier,
        request.password,
        employee_id=request.employee_id,
        remember_me=request.remember_me,
        platform=request.platform,
    )


@router.post(
    "/token",
    response_model=TokenResponse,
)
def login_for_swagger(
    http: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    return _sign_in(db, http, form_data.username, form_data.password, platform="web")


class RefreshTokenRequest(BaseModel):
    refresh_token: str
    platform: Optional[str] = None
    app_version: Optional[str] = None


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh_token(
    request: RefreshTokenRequest,
    http: Request,
    db: Session = Depends(get_db),
):
    try:
        access_token, new_refresh, session, user = refresh_session(
            db,
            request.refresh_token,
            ip=client_ip(http),
            user_agent=client_user_agent(http),
            platform=request.platform,
            app_version=request.app_version,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return _to_token_response(access_token, user, new_refresh, session)


@router.post("/logout")
def logout(
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    end_session(db, session, "sign_out")
    return {"message": "Signed out."}


class AppAccessRequest(BaseModel):
    event: Literal["launch", "resume"]
    platform: Optional[str] = None
    app_version: Optional[str] = None


@router.post("/access", status_code=204)
def record_app_access(
    request: AppAccessRequest,
    http: Request,
    user: Optional[User] = Depends(get_optional_current_user),
    session: Optional[UserSession] = Depends(get_optional_current_session),
    db: Session = Depends(get_db),
):
    """Called by the app on every launch and on return after 5+ minutes away, signed in or not."""
    log_app_access(
        db,
        request.event,
        user=user,
        session=session,
        platform=request.platform,
        app_version=request.app_version,
        ip=client_ip(http),
        user_agent=client_user_agent(http),
    )
    return Response(status_code=204)


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "official_email": current_user.official_email,
        "usn": current_user.usn,
        "employee_id": current_user.employee_id,
        "role_id": current_user.role_id,
        "role": current_user.role.name if current_user.role else "Student",
        "department_id": current_user.department_id,
        "department": current_user.department.name if current_user.department else None,
    }


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class DirectPasswordResetRequest(BaseModel):
    identifier: str
    current_password: str
    new_password: str

@router.post("/update-password")
def update_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    current_session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException
    from app.core.password import verify_password, hash_password

    if not verify_password(request.current_password, str(current_user.password_hash)):
        raise HTTPException(status_code=400, detail="Incorrect current password.")

    setattr(current_user, "password_hash", hash_password(request.new_password))
    db.commit()
    # Keep this device signed in; every other device must sign in with the new password
    keep = getattr(current_session, "id", None)
    for other in db.query(UserSession).filter(
        UserSession.user_id == current_user.id, UserSession.ended_at.is_(None), UserSession.id != keep
    ).all():
        end_session(db, other, "password_changed")
    return {"message": "Password updated successfully."}

@router.post("/reset-password-direct")
@limiter.limit("5/15minutes")
def reset_password_direct(
    request: Request,
    body: DirectPasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Change a password with the current one, without a session (fallback when the token has expired)."""
    from app.core.password import hash_password

    ip, ua = client_ip(request), client_user_agent(request)
    try:
        user = check_credentials(db, body.identifier, body.current_password)
    except SignInRefused as refused:
        log_sign_in(db, body.identifier, False, refused.reason, ip, ua, None, user=refused.user)
        raise HTTPException(status_code=400, detail=str(refused))

    setattr(user, "password_hash", hash_password(body.new_password))
    db.commit()
    end_all_user_sessions(db, user.id, "password_changed")
    log_sign_in(db, body.identifier, True, "password_changed", ip, ua, None, user=user)
    return {"message": "Password updated successfully."}


@router.get("/admin-only")
def admin_only(
    current_user: User = Depends(
        require_roles("Developer"),
    ),
):
    return {
        "message": "Welcome Developer!",
        "user": current_user.official_email,
    }
