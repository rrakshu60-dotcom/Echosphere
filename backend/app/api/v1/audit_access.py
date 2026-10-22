"""
Admin views of the sign-in log, app-access log and sessions (Dev Admin and College Admin only).
Every list supports search (q), filters, a date range, sorting and pages.
"""
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models.app_access_log import AppAccessLog
from app.models.sign_in_log import SignInLog
from app.models.user import User
from app.models.user_session import UserSession
from app.services.audit_log_service import create_audit_log_service
from app.services.session_service import _now, end_session, is_session_open

router = APIRouter(prefix="/audit", tags=["Audit & Logs"])

audit_admin = require_roles("Dev Admin", "College Admin")


def _page(query, model, q_columns, q, sort_column, order, page, page_size, start, end, to_dict):
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(*[c.ilike(like) for c in q_columns]))
    if start:
        query = query.filter(model.created_at >= start)
    if end:
        query = query.filter(model.created_at <= end)
    total = query.count()
    ordering = sort_column.asc() if order == "asc" else sort_column.desc()
    rows = query.order_by(ordering, model.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [to_dict(r) for r in rows], "total": total, "page": page, "page_size": page_size}


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


def _sign_in_dict(r: SignInLog) -> dict:
    return {
        "id": r.id, "at": _iso(r.created_at), "identifier": r.identifier, "user_id": r.user_id,
        "user_name": r.user_name, "role": r.role, "success": r.success, "reason": r.reason,
        "ip": r.ip, "platform": r.platform, "user_agent": r.user_agent, "session_id": r.session_id,
    }


def _access_dict(r: AppAccessLog) -> dict:
    return {
        "id": r.id, "at": _iso(r.created_at), "event": r.event, "user_id": r.user_id, "user_name": r.user_name,
        "session_id": r.session_id, "platform": r.platform, "app_version": r.app_version,
        "ip": r.ip, "user_agent": r.user_agent,
    }


def _session_dict(r: UserSession) -> dict:
    return {
        "id": r.id, "user_id": r.user_id, "user_name": r.user_name, "active": is_session_open(r),
        "remember_me": r.remember_me, "platform": r.platform, "user_agent": r.user_agent, "ip": r.ip,
        "last_ip": r.last_ip, "started_at": _iso(r.created_at), "last_seen_at": _iso(r.last_seen_at),
        "expires_at": _iso(r.expires_at), "ended_at": _iso(r.ended_at), "end_reason": r.end_reason,
        "ended_by_user_id": r.ended_by_user_id,
    }


Order = Literal["asc", "desc"]


@router.get("/sign-ins")
def list_sign_ins(
    q: Optional[str] = None,
    success: Optional[bool] = None,
    platform: Optional[str] = None,
    start: Optional[datetime] = Query(None, alias="from"),
    end: Optional[datetime] = Query(None, alias="to"),
    sort: Literal["at", "identifier", "user_name", "ip"] = "at",
    order: Order = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(audit_admin),
):
    query = db.query(SignInLog)
    if success is not None:
        query = query.filter(SignInLog.success == success)
    if platform:
        query = query.filter(SignInLog.platform == platform)
    sort_col = {"at": SignInLog.created_at, "identifier": SignInLog.identifier,
                "user_name": SignInLog.user_name, "ip": SignInLog.ip}[sort]
    return _page(query, SignInLog, [SignInLog.identifier, SignInLog.user_name, SignInLog.ip, SignInLog.reason],
                 q, sort_col, order, page, page_size, start, end, _sign_in_dict)


@router.get("/access")
def list_app_access(
    q: Optional[str] = None,
    event: Optional[Literal["launch", "resume", "refresh"]] = None,
    platform: Optional[str] = None,
    signed_in: Optional[bool] = None,
    start: Optional[datetime] = Query(None, alias="from"),
    end: Optional[datetime] = Query(None, alias="to"),
    sort: Literal["at", "user_name", "ip", "platform"] = "at",
    order: Order = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(audit_admin),
):
    query = db.query(AppAccessLog)
    if event:
        query = query.filter(AppAccessLog.event == event)
    if platform:
        query = query.filter(AppAccessLog.platform == platform)
    if signed_in is not None:
        query = query.filter(AppAccessLog.user_id.isnot(None) if signed_in else AppAccessLog.user_id.is_(None))
    sort_col = {"at": AppAccessLog.created_at, "user_name": AppAccessLog.user_name,
                "ip": AppAccessLog.ip, "platform": AppAccessLog.platform}[sort]
    return _page(query, AppAccessLog, [AppAccessLog.user_name, AppAccessLog.ip, AppAccessLog.app_version],
                 q, sort_col, order, page, page_size, start, end, _access_dict)


@router.get("/sessions")
def list_sessions(
    q: Optional[str] = None,
    state: Optional[Literal["active", "ended"]] = None,
    platform: Optional[str] = None,
    start: Optional[datetime] = Query(None, alias="from"),
    end: Optional[datetime] = Query(None, alias="to"),
    sort: Literal["started", "last_seen", "user_name"] = "last_seen",
    order: Order = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(audit_admin),
):
    query = db.query(UserSession)
    if state == "ended":
        # ended explicitly, or ran out of time
        now = _now()
        query = query.filter(or_(UserSession.ended_at.isnot(None), UserSession.expires_at <= now))
    elif state == "active":
        query = query.filter(UserSession.ended_at.is_(None), UserSession.expires_at > _now())
    if platform:
        query = query.filter(UserSession.platform == platform)
    if q:
        # also match by the user's sign-in identifiers
        like = f"%{q.strip()}%"
        ids = [u.id for u in db.query(User.id).filter(or_(
            User.username.ilike(like), User.usn.ilike(like), User.official_email.ilike(like), User.employee_id.ilike(like)
        )).all()]
        query = query.filter(or_(UserSession.user_name.ilike(like), UserSession.ip.ilike(like),
                                 UserSession.last_ip.ilike(like), UserSession.user_id.in_(ids or [-1])))
    sort_col = {"started": UserSession.created_at, "last_seen": UserSession.last_seen_at,
                "user_name": UserSession.user_name}[sort]
    result = _page(query, UserSession, [], None, sort_col, order, page, page_size, start, end, _session_dict)
    if state == "active":
        # idle-expired remembered sessions are not active even before expires_at
        result["items"] = [s for s in result["items"] if s["active"]]
    return result


@router.post("/sessions/{session_id}/end")
def end_user_session(
    session_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(audit_admin),
):
    session = db.get(UserSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    end_session(db, session, "ended_by_admin", ended_by=admin)
    create_audit_log_service(
        db=db,
        user_id=admin.id,
        action="END_SESSION",
        entity="SESSION",
        entity_id=session.id,
        description=f"{admin.full_name} signed out session #{session.id} of {session.user_name} ({session.platform or 'unknown device'}).",
    )
    return _session_dict(session)
