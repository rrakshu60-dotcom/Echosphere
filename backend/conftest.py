"""
Test isolation for backend unit tests (.agents/rules/testing.md §2-3).

- Every run gets a fresh temporary SQLite database; pytest refuses to start if DATABASE_URL
  points at Postgres/Supabase, so unit tests can never touch production.
- Outbound network access is blocked and AI model providers are switched off, so AI, speech,
  Hugging Face and push services must be faked.
"""
import os
import shutil
import socket
import tempfile

import pytest

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "testserver"}
_tmp_dir = None


def _is_local(address) -> bool:
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, bytes):
        host = host.decode()
    return host is None or str(host) in _LOCAL_HOSTS


def _block_outbound_network():
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def refuse(target):
        raise OSError(f"network access is blocked in unit tests (tried {target!r}); fake the outside service")

    def getaddrinfo(host, *args, **kwargs):
        if not _is_local(host):
            refuse(host)
        return real_getaddrinfo(host, *args, **kwargs)

    def connect(self, address):
        if self.family != getattr(socket, "AF_UNIX", None) and not _is_local(address):
            refuse(address)
        return real_connect(self, address)

    def connect_ex(self, address):
        if self.family != getattr(socket, "AF_UNIX", None) and not _is_local(address):
            refuse(address)
        return real_connect_ex(self, address)

    socket.getaddrinfo = getaddrinfo
    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex


def pytest_configure(config):
    global _tmp_dir
    url = os.environ.get("DATABASE_URL", "")
    if url and not url.startswith("sqlite"):
        raise pytest.UsageError(
            "refusing to run unit tests: DATABASE_URL points at a non-SQLite database. "
            "Unit tests always use a temporary SQLite DB; production is only for backend/scripts/live_*.py."
        )

    # Never load backend/.env: its real secrets must not reach tests, and CI has no .env at all.
    import dotenv

    dotenv.load_dotenv = lambda *args, **kwargs: False

    # Known passwords for the seeded accounts (seeders read ES_PASSWORD_<USERNAME>).
    for username in ("ESDEV01", "CADMIN", "PRINCIPAL", "HOD_AIML", "1DB23CI079", "DBITAIMLT022022"):
        os.environ[f"ES_PASSWORD_{username}"] = f"unit-test-{username.lower()}"

    # No AI model answers unit tests, not even a local one on loopback: replies must be deterministic.
    os.environ.update(
        USE_FINE_TUNED_QWEN="false",
        USE_FINE_TUNED_GEMMA="false",
        GEMINI_API_KEY="",
        CLOUDFLARE_API_TOKEN="",
        CLOUDFLARE_ACCOUNT_ID="",
        LOCAL_LLM_PYTHON="",
    )

    _tmp_dir = tempfile.mkdtemp(prefix="echosphere_test_")
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp_dir, "test.db").replace("\\", "/")

    # Create the engine now, before any app module can reload .env over DATABASE_URL.
    from app.db.database import engine

    if engine.dialect.name != "sqlite":
        raise pytest.UsageError(f"refusing to run unit tests: engine resolved to {engine.dialect.name}")

    _block_outbound_network()


def pytest_unconfigure(config):
    if _tmp_dir:
        try:
            from app.db.database import engine

            engine.dispose()
        except Exception:
            pass
        shutil.rmtree(_tmp_dir, ignore_errors=True)
