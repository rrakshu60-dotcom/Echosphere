"""Unit tests must never reach production: temp SQLite only, no outbound network (.agents/rules/testing.md §2-3)."""
import os
import socket
import subprocess
import sys
import tempfile

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_engine_is_a_fresh_temporary_sqlite_db():
    from app.db.database import engine

    assert engine.dialect.name == "sqlite"
    db_path = os.path.abspath(engine.url.database)
    assert db_path.startswith(os.path.abspath(tempfile.gettempdir()))
    assert os.path.basename(db_path) != "echosphere.db"


def test_outbound_network_is_blocked():
    with pytest.raises(OSError, match="network access is blocked"):
        socket.create_connection(("example.com", 443), timeout=5)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres",
        "postgres://u:p@db.example.supabase.co:5432/postgres",
        "postgresql+psycopg2://u:p@localhost:5432/echosphere",
    ],
)
def test_pytest_refuses_to_start_on_a_postgres_url(url):
    env = {**os.environ, "DATABASE_URL": url}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "app/test_test_isolation.py"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode != 0
    assert "refusing to run unit tests" in (result.stdout + result.stderr)


def test_no_ai_model_provider_is_used():
    import app.services.model_router as mr

    router = mr.ModelRouter.get_instance()
    assert not (mr.USE_FINE_TUNED_QWEN and router.fine_tuned_qwen.is_configured())
    assert not (mr.USE_FINE_TUNED_GEMMA and router.fine_tuned_gemma.is_configured())
    assert not router.gemini_provider.is_configured()
    assert not router.cloudflare_provider.is_configured()


def test_backend_env_file_is_not_loaded():
    # Real secrets in backend/.env must never reach unit tests; CI has no .env at all.
    # Compare names only, so a failure never prints secret values.
    leaked = {"HF_TOKEN", "SG_DATABASE_URL", "OLD_MUMBAI_DATABASE_URL"} & set(os.environ)
    assert not leaked, f"backend/.env leaked into unit tests: {sorted(leaked)}"
    assert os.environ.get("ES_PASSWORD_ESDEV01", "").startswith("unit-test-"), "seeded test passwords not set"
