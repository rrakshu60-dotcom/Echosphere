"""
Permanent notice records (owner decisions 2026-10-22, step 2).

Every notice gets a NoticeRecord and a timeline of NoticeRecordEvents: created, edited (with the old
title and content), approved/rejected (with remarks), published, alerts and push sent, each speaker
play started/finished/stopped, deleted (by whom, before or after its first broadcast) and audio deleted.

Most of it is captured by one session hook, so every code path that touches a notice or a speaker
queue item is covered, including future ones. The hook writes in the same transaction as the change:
if the record cannot be written, the change (including a delete) is refused.

Who did it comes from the request's bearer token (set by the actor middleware in main.py);
background work (queue daemon, repeat scheduler, speaker callbacks) is recorded as "System".
"""
import logging
import os
import re
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import event, inspect, select, text
from sqlalchemy.orm import Session

from app.models.announcement import Announcement
from app.models.announcement_approval import AnnouncementApproval
from app.models.announcement_delivery import AnnouncementDelivery
from app.models.notice_record import NoticeRecord, NoticeRecordEvent
from app.models.speaker_queue import SpeakerQueue

logger = logging.getLogger("echosphere.notice_records")

# {"user_id": int, "role": str} for the request being handled, set by the actor middleware
current_actor: ContextVar[Optional[dict]] = ContextVar("current_actor", default=None)

_RECORDS = NoticeRecord.__table__
_EVENTS = NoticeRecordEvent.__table__
_PENDING_AUDIO_KEY = "notice_records_deleted_ids"
_PENDING_ATTACHMENTS_KEY = "notice_records_deleted_attachments"
STOPPED_STATUSES = {"Paused", "Held", "Skipped", "Cancelled", "Expired_Slot_Ended"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _value(v):
    return getattr(v, "value", v)


def _actor(conn) -> dict:
    actor = current_actor.get()
    if not actor or not actor.get("user_id"):
        return {"actor_id": None, "actor_name": "System", "actor_role": None}
    row = conn.execute(
        text("SELECT u.full_name, r.name FROM users u LEFT JOIN roles r ON r.id = u.role_id WHERE u.id = :id"),
        {"id": actor["user_id"]},
    ).first()
    return {
        "actor_id": actor["user_id"],
        "actor_name": row[0] if row else None,
        "actor_role": (row[1] if row else None) or actor.get("role"),
    }


def _user(conn, user_id) -> dict:
    if user_id is None:
        return {"name": None, "role": None, "department": None}
    row = conn.execute(
        text(
            "SELECT u.full_name, r.name, d.name FROM users u LEFT JOIN roles r ON r.id = u.role_id "
            "LEFT JOIN departments d ON d.id = u.department_id WHERE u.id = :id"
        ),
        {"id": user_id},
    ).first()
    return {"name": row[0], "role": row[1], "department": row[2]} if row else {"name": None, "role": None, "department": None}


def _add_event(conn, announcement_id: int, name: str, detail: str = "", actor: Optional[dict] = None) -> None:
    conn.execute(_EVENTS.insert().values(
        announcement_id=announcement_id, created_at=_now(), event=name, detail=detail, **(actor or _actor(conn))
    ))


def _update_record(conn, announcement_id: int, **values) -> None:
    conn.execute(_RECORDS.update().where(_RECORDS.c.announcement_id == announcement_id).values(**values))


def _record_row(conn, announcement_id: int):
    return conn.execute(select(_RECORDS).where(_RECORDS.c.announcement_id == announcement_id)).first()


def _channels(conn, announcement_id: int) -> Optional[str]:
    rows = conn.execute(
        text(
            "SELECT dt.name FROM announcement_deliveries d JOIN delivery_types dt ON dt.id = d.delivery_type_id "
            "WHERE d.announcement_id = :id ORDER BY dt.name"
        ),
        {"id": announcement_id},
    ).fetchall()
    return ",".join(r[0] for r in rows) or None


def _mark_delivered(conn, announcement_id: int, at: datetime) -> None:
    row = _record_row(conn, announcement_id)
    if row is None:
        return
    values = {"last_delivered_at": at}
    if row.first_delivered_at is None:
        values["first_delivered_at"] = at
    _update_record(conn, announcement_id, **values)


# ---------------------------------------------------------------- what the hook records


def _record_creation(conn, ann: Announcement) -> None:
    creator = _user(conn, ann.created_by)
    category = conn.execute(text("SELECT name FROM announcement_categories WHERE id = :id"), {"id": ann.category_id}).scalar()
    status = _value(ann.status)
    now = _now()
    conn.execute(_RECORDS.insert().values(
        announcement_id=ann.id,
        original_title=ann.title,
        original_content=ann.description,
        creator_id=ann.created_by,
        creator_name=creator["name"],
        creator_role=creator["role"],
        creator_department=creator["department"],
        created_at=ann.created_at or now,
        title=ann.title,
        content=ann.description,
        category=category,
        priority=_value(ann.priority),
        emergency_level=_value(ann.emergency_level),
        target_audience=ann.target_audience,
        status=status,
        scheduled_at=ann.scheduled_at,
        published_at=now if status == "Published" else None,
        speaker_play_count=0,
        partial=False,
    ))
    _add_event(conn, ann.id, "CREATED", f"Created as {status}. Category: {category}. Audience: {ann.target_audience or '-'}.")
    if status == "Published":
        _add_event(conn, ann.id, "PUBLISHED", "Published on creation.")
    elif status == "Scheduled":
        _add_event(conn, ann.id, "SCHEDULED", f"Scheduled for {ann.scheduled_at} UTC.")


def _record_changes(conn, ann: Announcement) -> None:
    state = inspect(ann)

    def change(attr):
        hist = state.attrs[attr].history
        if not hist.has_changes():
            return None
        old = hist.deleted[0] if hist.deleted else None
        return _value(old), _value(getattr(ann, attr))

    values, changed = {}, []
    title, content = change("title"), change("description")
    if title or content:
        old_title = title[0] if title else ann.title
        old_content = content[0] if content else ann.description
        _add_event(conn, ann.id, "EDITED", f"Previous title: {old_title}\nPrevious content: {old_content}")
        values.update(title=ann.title, content=ann.description)

    for attr, column in (("priority", "priority"), ("emergency_level", "emergency_level"),
                         ("target_audience", "target_audience"), ("scheduled_at", "scheduled_at")):
        c = change(attr)
        if c and c[0] != c[1]:
            values[column] = c[1]
            changed.append(f"{attr.replace('_', ' ')}: {c[0]} -> {c[1]}")
    if changed:
        _add_event(conn, ann.id, "SETTINGS_CHANGED", "; ".join(changed))

    status = change("status")
    if status and status[0] != status[1]:
        new = status[1]
        values["status"] = new
        if new == "Published":
            values["published_at"] = _now()
            _add_event(conn, ann.id, "PUBLISHED", f"Status {status[0]} -> Published.")
        elif new == "Scheduled":
            _add_event(conn, ann.id, "SCHEDULED", f"Scheduled for {ann.scheduled_at} UTC.")
        elif new == "Archived":
            _add_event(conn, ann.id, "ARCHIVED", "")
        elif new not in ("Rejected",):  # rejection is recorded with its remarks from the approval row
            _add_event(conn, ann.id, "STATUS_CHANGED", f"{status[0]} -> {new}")

    if values:
        _update_record(conn, ann.id, **values)


def _record_approval(conn, approval: AnnouncementApproval) -> None:
    approver = _user(conn, approval.approver_id)
    decision = "APPROVED" if str(approval.status).lower().startswith("approv") else "REJECTED"
    remarks = approval.remarks or ""
    _add_event(conn, approval.announcement_id, decision, f"Remarks: {remarks}" if remarks else "No remarks.",
               actor={"actor_id": approval.approver_id, "actor_name": approver["name"], "actor_role": approver["role"]})
    if decision == "REJECTED":
        _update_record(conn, approval.announcement_id, status="Rejected")


def _speaker_detail(conn, item: SpeakerQueue) -> str:
    node = conn.execute(text("SELECT name FROM speaker_nodes WHERE id = :id"), {"id": item.speaker_node_id}).scalar()
    played = conn.execute(
        text("SELECT total_played_count FROM announcement_repeat_schedules WHERE announcement_id = :id"),
        {"id": item.announcement_id},
    ).scalar()
    detail = f"Speaker: {node or 'any speaker'}"
    if played is not None:
        detail += f". Repeat round {int(played) + 1}"
    return detail + "."


def _record_speaker(conn, item: SpeakerQueue, old_status: Optional[str]) -> None:
    new = item.status
    if old_status == new or _record_row(conn, item.announcement_id) is None:
        return
    system = {"actor_id": None, "actor_name": "System", "actor_role": None}
    if new == "Playing":
        _add_event(conn, item.announcement_id, "SPEAKER_STARTED", _speaker_detail(conn, item), actor=system)
        _mark_delivered(conn, item.announcement_id, _now())
    elif old_status == "Playing" and new == "Completed":
        _add_event(conn, item.announcement_id, "SPEAKER_FINISHED", _speaker_detail(conn, item), actor=system)
        row = _record_row(conn, item.announcement_id)
        _update_record(conn, item.announcement_id, speaker_play_count=(row.speaker_play_count or 0) + 1, last_delivered_at=_now())
    elif old_status == "Playing" and new in STOPPED_STATUSES:
        _add_event(conn, item.announcement_id, "SPEAKER_STOPPED", f"{_speaker_detail(conn, item)} Now {new}.")


def _record_deletion(conn, ann: Announcement) -> None:
    """Write the deletion footprint. Raising here refuses the delete (same transaction)."""
    actor = _actor(conn)
    row = _record_row(conn, ann.id)
    if row is None:  # a notice older than the record system: keep what is known now
        _record_creation(conn, ann)
        _update_record(conn, ann.id, partial=True)
        row = _record_row(conn, ann.id)
    before_broadcast = row.first_delivered_at is None and (row.speaker_play_count or 0) == 0
    _update_record(
        conn, ann.id,
        title=ann.title, content=ann.description, status=_value(ann.status),
        deleted_at=_now(), deleted_by_id=actor["actor_id"], deleted_by_name=actor["actor_name"],
        deleted_by_role=actor["actor_role"], deleted_before_broadcast=before_broadcast,
    )
    _add_event(conn, ann.id, "DELETED",
               "Deleted before its first broadcast." if before_broadcast else "Deleted after it was delivered.",
               actor=actor)


# ---------------------------------------------------------------- explicit events (bulk paths the hook can't see)


def log_notice_event(db: Session, announcement_id: int, name: str, detail: str = "", delivered: bool = False) -> None:
    """Record an event the session hook can't see (bulk inserts such as alerts, external push)."""
    conn = db.connection()
    if _record_row(conn, announcement_id) is None:
        return
    _add_event(conn, announcement_id, name, detail)
    if delivered:
        _mark_delivered(conn, announcement_id, _now())
    db.commit()


# ---------------------------------------------------------------- audio clean-up after deletion


def _delete_local_audio(announcement_id: int) -> int:
    from app.services import tts_service

    folder = tts_service.STATIC_AUDIO_DIR
    pattern = re.compile(rf"^announcement_{announcement_id}(_|\.)")
    removed = 0
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            if pattern.match(name):
                try:
                    os.remove(os.path.join(folder, name))
                    removed += 1
                except OSError as exc:
                    logger.warning(f"Could not delete {name}: {exc}")
    return removed


def _delete_cloud_audio(announcement_id: int) -> int:
    from app.services.cloud_storage_service import CloudStorageService

    return CloudStorageService.delete_announcement_audio(announcement_id)


def delete_notice_audio(announcement_id: int, session_factory) -> None:
    """Remove a deleted notice's audio from Render and the cloud backup, then record it."""
    local = _delete_local_audio(announcement_id)
    try:
        cloud = _delete_cloud_audio(announcement_id)
        cloud_note = f"{cloud} cloud backup file(s)"
    except Exception as exc:
        logger.warning(f"Cloud audio delete failed for #{announcement_id}: {exc}")
        cloud_note = "cloud backup could not be reached"
    with session_factory() as db:
        conn = db.connection()
        _add_event(conn, announcement_id, "AUDIO_DELETED", f"Removed {local} local audio file(s) and {cloud_note}.",
                   actor={"actor_id": None, "actor_name": "System", "actor_role": None})
        _update_record(conn, announcement_id, audio_deleted_at=_now())
        db.commit()


def purge_audio_of_deleted_notices(session_factory) -> list:
    """
    Remove the audio of every deleted notice whose audio is still stored (e.g. deleted before the record
    system existed): local files, then all cloud backups in one commit, then AUDIO_DELETED on each record.
    If the cloud backup can't be reached, nothing is marked, so the next run retries. Returns the cleaned IDs.
    """
    from app.services.cloud_storage_service import CloudStorageService

    with session_factory() as db:
        ids = [r[0] for r in db.execute(
            select(_RECORDS.c.announcement_id).where(_RECORDS.c.deleted_at.isnot(None), _RECORDS.c.audio_deleted_at.is_(None))
        ).all()]
    if not ids:
        return []
    local = {nid: _delete_local_audio(nid) for nid in ids}
    try:
        cloud = CloudStorageService.delete_audio_for_notices(ids)
    except Exception as exc:
        logger.warning(f"Audio cleanup of {len(ids)} deleted notice(s) postponed, cloud backup unreachable: {exc}")
        return []
    system = {"actor_id": None, "actor_name": "System", "actor_role": None}
    with session_factory() as db:
        conn = db.connection()
        for nid in ids:
            _add_event(conn, nid, "AUDIO_DELETED",
                       f"Removed {local[nid]} local audio file(s) and {cloud.get(nid, 0)} cloud backup file(s) "
                       f"(clean-up of a notice deleted earlier).", actor=system)
            _update_record(conn, nid, audio_deleted_at=_now())
        db.commit()
    logger.info(f"Removed audio of {len(ids)} deleted notice(s)")
    return ids


def purge_orphaned_audio(session_factory) -> list:
    """
    Remove audio that belongs to no notice at all: no announcement and no notice record (e.g. from an
    older database, or the speech diagnostic's made-up IDs). Audio of notices that exist, and of deleted
    notices with a record, is never touched here. Returns the removed IDs.
    """
    from app.services import tts_service
    from app.services.cloud_storage_service import CloudStorageService

    candidates = set(CloudStorageService.list_notice_audio_ids())
    folder = tts_service.STATIC_AUDIO_DIR
    if os.path.isdir(folder):
        pattern = re.compile(r"^announcement_(\d+)(_|\.)")
        candidates |= {int(m.group(1)) for name in os.listdir(folder) for m in [pattern.match(name)] if m}
    if not candidates:
        return []
    with session_factory() as db:
        known = {r[0] for r in db.execute(text("SELECT id FROM announcements")).all()}
        known |= {r[0] for r in db.execute(select(_RECORDS.c.announcement_id)).all()}
    orphans = sorted(candidates - known)
    if not orphans:
        return []
    for nid in orphans:
        _delete_local_audio(nid)
    CloudStorageService.delete_audio_for_notices(orphans)
    logger.info(f"Removed audio of {len(orphans)} ID(s) with no notice and no record: {orphans}")
    return orphans


def notice_was_deleted(announcement_id: int) -> bool:
    from app.db.database import SessionLocal

    with SessionLocal() as db:
        deleted_at = db.execute(
            select(_RECORDS.c.deleted_at).where(_RECORDS.c.announcement_id == announcement_id)
        ).scalar()
    return deleted_at is not None


def discard_audio_if_notice_deleted(announcement_id: int) -> None:
    """A speech job can finish after its notice was deleted: remove what it wrote, and record it."""
    if not notice_was_deleted(announcement_id):
        return
    removed = _delete_local_audio(announcement_id)
    if removed:
        from app.db.database import SessionLocal

        with SessionLocal() as db:
            _add_event(db.connection(), announcement_id, "AUDIO_DELETED",
                       f"Removed {removed} audio file(s) generated after the notice was deleted.",
                       actor={"actor_id": None, "actor_name": "System", "actor_role": None})
            db.commit()


# ---------------------------------------------------------------- the hook


def _delete_attachments(files, session_factory) -> None:
    """Deletes a deleted notice's attachment files, except any another notice still uses (a staff member could
    copy someone else's attachment link into their own notice and delete it)."""
    from sqlalchemy import String, cast
    from app.services.cloud_storage_service import CloudStorageService
    try:
        with session_factory() as db:
            files = [f for f in files if not db.query(Announcement.id).filter(
                cast(Announcement.attachments, String).like(f"%/{f}%")).first()]
        if files:
            CloudStorageService.delete_attachment_files(files)
    except Exception as exc:
        logger.warning(f"Could not delete attachments {files}: {exc}")


def install_notice_record_hooks(session_factory) -> None:
    # Load a queue item's previous status whenever it changes, even after a commit expired it,
    # so Playing -> Completed is always visible to the hook.
    event.listen(SpeakerQueue.status, "set", lambda target, value, old, initiator: value, active_history=True)

    @event.listens_for(session_factory, "after_flush")
    def _capture(session, flush_context):
        conn = session.connection()
        channel_changes = {
            obj.announcement_id
            for obj in list(session.new) + list(session.deleted)
            if isinstance(obj, AnnouncementDelivery)
        }
        for obj in session.new:
            if isinstance(obj, Announcement):
                _record_creation(conn, obj)
            elif isinstance(obj, AnnouncementApproval):
                _record_approval(conn, obj)
            elif isinstance(obj, SpeakerQueue) and obj.status == "Playing":
                _record_speaker(conn, obj, None)
        for obj in session.dirty:
            if isinstance(obj, Announcement) and session.is_modified(obj, include_collections=False):
                if _record_row(conn, obj.id) is not None:
                    _record_changes(conn, obj)
            elif isinstance(obj, SpeakerQueue):
                hist = inspect(obj).attrs.status.history
                if hist.has_changes():
                    _record_speaker(conn, obj, hist.deleted[0] if hist.deleted else None)
        for obj in session.deleted:
            if isinstance(obj, Announcement):
                _record_deletion(conn, obj)
                session.info.setdefault(_PENDING_AUDIO_KEY, set()).add(obj.id)
                files = [str(a.get("url", "")).rsplit("/", 1)[-1] for a in (obj.attachments or []) if isinstance(a, dict)]
                if files:
                    session.info.setdefault(_PENDING_ATTACHMENTS_KEY, {})[obj.id] = files
                channel_changes.discard(obj.id)
        for nid in channel_changes:
            _update_record(conn, nid, channels=_channels(conn, nid))

    @event.listens_for(session_factory, "after_commit")
    def _clean_audio(session):
        ids = session.info.pop(_PENDING_AUDIO_KEY, None)
        for nid in ids or ():
            threading.Thread(target=delete_notice_audio, args=(nid, session_factory), daemon=True,
                             name=f"NoticeAudioDelete-{nid}").start()
        # A deleted notice's attachments go too (they'd otherwise stay in cloud storage forever)
        for nid, files in (session.info.pop(_PENDING_ATTACHMENTS_KEY, None) or {}).items():
            threading.Thread(target=_delete_attachments, args=(files, session_factory), daemon=True,
                             name=f"NoticeAttachmentDelete-{nid}").start()

    @event.listens_for(session_factory, "after_rollback")
    def _forget(session):
        session.info.pop(_PENDING_AUDIO_KEY, None)
        session.info.pop(_PENDING_ATTACHMENTS_KEY, None)
