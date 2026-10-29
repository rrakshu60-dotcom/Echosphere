"""Test-only helper: a bearer header backed by a real session, as login would create it."""
import os

# Every test file imports this. Outside pytest's conftest (temporary SQLite) the app would use backend/.env,
# i.e. the production database: a test run that way once published test notices on the live system.
if not os.environ.get("DATABASE_URL", "").startswith("sqlite"):
    raise RuntimeError("Tests must run through pytest in backend/ (conftest.py uses a temporary SQLite database).")

from app.db.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.session_service import create_session  # noqa: E402


def bearer(username: str, remember_me: bool = False) -> dict:
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).one()
        access_token, _refresh, _session = create_session(
            db, user, remember_me=remember_me, ip="127.0.0.1", user_agent="pytest", platform="test"
        )
    return {"Authorization": f"Bearer {access_token}"}


TEST_SPEAKER_MAC = "AA:BB:CC:00:11:22"


def speaker_headers(mac: str = TEST_SPEAKER_MAC) -> dict:
    """Headers a speaker sends: its MAC and its device key."""
    from app.core.speaker_auth import SPEAKER_KEY_HEADER, device_key_for

    return {"X-Speaker-Mac": mac, SPEAKER_KEY_HEADER: device_key_for(mac)}
