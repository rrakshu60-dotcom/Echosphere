"""
Signed-in sessions, the sign-in log and the app-access log (owner decisions 2026-10-22).

- Sign-in creates a session: a 30-minute access token that names the session (claim "sid") plus a
  refresh key. Only the key's SHA-256 is stored; every refresh replaces the key.
- "Remember me": ends after 7 days unused or 30 days total. Otherwise: 12 hours.
- Every request checks the session is still open and the account still active, so signing out,
  an admin ending the session, a password reset or disabling the account take effect at once.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.jwt_handler import create_access_token
from app.models.app_access_log import AppAccessLog
from app.models.sign_in_log import SignInLog
from app.models.user import User
from app.models.user_session import UserSession

ACCESS_TOKEN_LIFETIME = timedelta(minutes=30)
REMEMBER_IDLE_LIMIT = timedelta(days=7)
REMEMBER_MAX_AGE = timedelta(days=30)
SESSION_MAX_AGE = timedelta(hours=12)
ACCESS_LOG_RETENTION = timedelta(days=90)

PLATFORMS = {"web", "android", "ios", "windows", "macos", "linux", "test"}
ACCESS_EVENTS = {"launch", "resume", "refresh"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash(refresh_key: str) -> str:
    return hashlib.sha256(refresh_key.encode()).hexdigest()


def clean_platform(platform: Optional[str]) -> Optional[str]:
    if not platform:
        return None
    p = platform.strip().lower()
    return p if p in PLATFORMS else "other"


def client_ip(request: Request) -> Optional[str]:
    """The address Render's proxy saw: the last X-Forwarded-For entry (earlier ones are client-supplied)."""
    forwarded = request.headers.get("x-forwarded-for", "")
    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    if hops:
        return hops[-1][:64]
    return request.client.host if request.client else None


def client_user_agent(request: Request) -> Optional[str]:
    ua = request.headers.get("user-agent")
    return ua[:300] if ua else None


def _issue_access_token(user: User, session: UserSession) -> str:
    return create_access_token(
        {
            "sub": user.official_email or user.usn or user.username,
            "role": user.role.name if user.role else "Student",
            "user_id": user.id,
            "sid": session.id,
        },
        expires_in=ACCESS_TOKEN_LIFETIME,
    )


def create_session(
    db: Session,
    user: User,
    remember_me: bool,
    ip: Optional[str],
    user_agent: Optional[str],
    platform: Optional[str],
) -> Tuple[str, str, UserSession]:
    """Open a session for a signed-in user. Returns (access_token, refresh_key, session)."""
    now = _now()
    refresh_key = secrets.token_urlsafe(32)
    session = UserSession(
        user_id=user.id,
        user_name=user.full_name,
        refresh_hash=_hash(refresh_key),
        remember_me=bool(remember_me),
        platform=clean_platform(platform),
        user_agent=user_agent,
        ip=ip,
        last_ip=ip,
        created_at=now,
        last_seen_at=now,
        expires_at=now + (REMEMBER_MAX_AGE if remember_me else SESSION_MAX_AGE),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _issue_access_token(user, session), refresh_key, session


def is_session_open(session: Optional[UserSession], now: Optional[datetime] = None) -> bool:
    if session is None or session.ended_at is not None:
        return False
    now = now or _now()
    if now >= session.expires_at:
        return False
    if session.remember_me and now >= session.last_seen_at + REMEMBER_IDLE_LIMIT:
        return False
    return True


def session_for_request(db: Session, session_id) -> Optional[UserSession]:
    """The session a request's access token names, if it is still open."""
    if not isinstance(session_id, int):
        return None
    session = db.get(UserSession, session_id)
    return session if is_session_open(session) else None


def refresh_session(
    db: Session,
    refresh_key: str,
    ip: Optional[str],
    user_agent: Optional[str],
    platform: Optional[str],
    app_version: Optional[str],
) -> Tuple[str, str, UserSession, User]:
    """Swap a refresh key for a new access token and a new key. Raises ValueError if refused."""
    session = db.query(UserSession).filter(UserSession.refresh_hash == _hash(refresh_key)).first()
    if not is_session_open(session):
        raise ValueError("Session has ended. Please sign in again.")
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        end_session(db, session, "account_disabled")
        raise ValueError("Session has ended. Please sign in again.")

    new_key = secrets.token_urlsafe(32)
    session.refresh_hash = _hash(new_key)
    session.last_seen_at = _now()
    session.last_ip = ip
    db.commit()

    log_app_access(db, "refresh", user=user, session=session, platform=platform,
                   app_version=app_version, ip=ip, user_agent=user_agent)
    return _issue_access_token(user, session), new_key, session, user


def end_session(db: Session, session: UserSession, reason: str, ended_by: Optional[User] = None) -> None:
    if session.ended_at is None:
        session.ended_at = _now()
        session.end_reason = reason
        session.ended_by_user_id = ended_by.id if ended_by else None
        db.commit()


def end_all_user_sessions(db: Session, user_id: int, reason: str) -> int:
    open_sessions = db.query(UserSession).filter(UserSession.user_id == user_id, UserSession.ended_at.is_(None)).all()
    now = _now()
    for s in open_sessions:
        s.ended_at = now
        s.end_reason = reason
    db.commit()
    return len(open_sessions)


def log_sign_in(
    db: Session,
    identifier: str,
    success: bool,
    reason: str,
    ip: Optional[str],
    user_agent: Optional[str],
    platform: Optional[str],
    user: Optional[User] = None,
    session: Optional[UserSession] = None,
) -> None:
    db.add(SignInLog(
        identifier=(identifier or "")[:255],
        user_id=user.id if user else None,
        user_name=user.full_name if user else None,
        role=(user.role.name if user and user.role else None),
        success=success,
        reason=reason,
        ip=ip,
        user_agent=user_agent,
        platform=clean_platform(platform),
        session_id=session.id if session else None,
    ))
    db.commit()


def log_app_access(
    db: Session,
    event: str,
    user: Optional[User],
    session: Optional[UserSession],
    platform: Optional[str],
    app_version: Optional[str],
    ip: Optional[str],
    user_agent: Optional[str],
) -> None:
    db.add(AppAccessLog(
        event=event,
        user_id=user.id if user else None,
        user_name=user.full_name if user else None,
        session_id=session.id if session else None,
        platform=clean_platform(platform),
        app_version=(app_version or "")[:30] or None,
        ip=ip,
        user_agent=user_agent,
    ))
    if session is not None and event in ("launch", "resume"):
        session.last_seen_at = _now()
        session.last_ip = ip
    db.commit()


def purge_old_access_logs(db: Session) -> int:
    """Delete app-access entries older than 90 days (free-tier storage limit). Other logs are kept forever."""
    removed = (
        db.query(AppAccessLog)
        .filter(AppAccessLog.created_at < _now() - ACCESS_LOG_RETENTION)
        .delete(synchronize_session=False)
    )
    db.commit()
    return removed
