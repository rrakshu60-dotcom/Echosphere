"""Test-only helper: a bearer header backed by a real session, as login would create it."""
from app.db.database import SessionLocal
from app.models.user import User
from app.services.session_service import create_session


def bearer(username: str, remember_me: bool = False) -> dict:
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).one()
        access_token, _refresh, _session = create_session(
            db, user, remember_me=remember_me, ip="127.0.0.1", user_agent="pytest", platform="test"
        )
    return {"Authorization": f"Bearer {access_token}"}
