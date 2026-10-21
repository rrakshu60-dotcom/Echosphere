"""
Event-driven wake signal for the speaker queue & repeat scheduler daemon.

Instead of polling the database on a fixed 2s / 4s timer, the daemon sleeps on a
threading.Event and is woken:
  1. Instantly, whenever any request commits a change to the speaker queue,
     a repeat schedule, or an announcement (publish / approve / delete / emergency).
  2. Exactly at the next known due time (current notice finishes, a queued notice's
     scheduled_time arrives, a repeat's next_repeat_at arrives, or an IST minute
     boundary where a break / custom window can open or close).

Result: queue transitions and repeat dispatches happen with ~0s scheduling lag,
without hammering Supabase with a busy loop.
"""

import threading
from typing import Iterable

from sqlalchemy import event

_wake_event = threading.Event()

# Tables whose changes should immediately wake the scheduler.
_WATCHED_TABLES = {
    "speaker_queue",
    "announcement_repeat_schedules",
    "announcements",
}

# Session.info flag used by the daemon's own sessions so its commits don't re-wake itself
DAEMON_SESSION_FLAG = "queue_daemon"
_DIRTY_FLAG = "_queue_signal_dirty"


def notify_queue_change() -> None:
    """Wake the scheduler daemon immediately."""
    _wake_event.set()


def wait_for_queue_change(timeout: float) -> bool:
    """Block until notified or timeout elapses. Returns True if woken by a change."""
    woke = _wake_event.wait(timeout=max(0.0, timeout))
    _wake_event.clear()
    return woke


def _touches_watched_table(objs: Iterable) -> bool:
    for obj in objs:
        table = getattr(obj, "__tablename__", None)
        if table in _WATCHED_TABLES:
            return True
    return False


def install_session_hooks(session_factory) -> None:
    """
    Attach SQLAlchemy listeners to the session factory so that ANY commit touching
    the queue / schedules / announcements wakes the daemon - no need to remember to
    call notify_queue_change() in every endpoint.
    """
    if getattr(session_factory, "_queue_signal_installed", False):
        return

    @event.listens_for(session_factory, "after_flush")
    def _mark_dirty(session, flush_context):
        if session.info.get(DAEMON_SESSION_FLAG):
            return
        if (
            _touches_watched_table(session.new)
            or _touches_watched_table(session.dirty)
            or _touches_watched_table(session.deleted)
        ):
            session.info[_DIRTY_FLAG] = True

    @event.listens_for(session_factory, "do_orm_execute")
    def _mark_dirty_bulk(orm_execute_state):
        # Bulk query(...).update() / .delete() calls bypass session.new/dirty/deleted
        session = orm_execute_state.session
        if session.info.get(DAEMON_SESSION_FLAG):
            return
        if not (orm_execute_state.is_update or orm_execute_state.is_delete or orm_execute_state.is_insert):
            return
        try:
            for mapper in orm_execute_state.all_mappers:
                if getattr(mapper.local_table, "name", None) in _WATCHED_TABLES:
                    session.info[_DIRTY_FLAG] = True
                    return
        except Exception:
            session.info[_DIRTY_FLAG] = True

    @event.listens_for(session_factory, "after_commit")
    def _wake_on_commit(session):
        if session.info.pop(_DIRTY_FLAG, False):
            notify_queue_change()

    @event.listens_for(session_factory, "after_rollback")
    def _clear_on_rollback(session):
        session.info.pop(_DIRTY_FLAG, None)

    session_factory._queue_signal_installed = True
