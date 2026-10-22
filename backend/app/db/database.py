import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv("DATABASE_URL")
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
canonical_db_path = os.path.join(backend_dir, "echosphere.db")

if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{canonical_db_path}"
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

if DATABASE_URL.startswith("sqlite"):
    if ":memory:" in DATABASE_URL:
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
        )

        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            try:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.close()
            except Exception:
                pass
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    # Host only (no credentials): shows in deploy logs which database region the backend uses
    print(f"[DB] PostgreSQL host: {engine.url.host}", flush=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_schema_migrations():
    """Idempotently ensures all required columns and indexes exist in the connected database."""
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            # Detect SQLite vs PostgreSQL
            is_sqlite = engine.url.get_backend_name() == "sqlite"
            if is_sqlite:
                # 1. announcements table
                try:
                    res = conn.execute(text("PRAGMA table_info(announcements);")).fetchall()
                    cols = [r[1] for r in res]
                    if cols:
                        if "target_audience" not in cols:
                            conn.execute(text("ALTER TABLE announcements ADD COLUMN target_audience VARCHAR(255) DEFAULT 'Entire College';"))
                        if "ai_summary" not in cols:
                            conn.execute(text("ALTER TABLE announcements ADD COLUMN ai_summary TEXT;"))
                        if "speaker_voice" not in cols:
                            conn.execute(text("ALTER TABLE announcements ADD COLUMN speaker_voice VARCHAR(20) DEFAULT 'female';"))
                except Exception:
                    pass

                # 2. announcement_repeat_schedules table
                try:
                    res = conn.execute(text("PRAGMA table_info(announcement_repeat_schedules);")).fetchall()
                    cols = [r[1] for r in res]
                    if cols:
                        if "repeat_mode" not in cols:
                            conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN repeat_mode VARCHAR(20) DEFAULT 'INTERVAL';"))
                        if "interval_minutes" not in cols:
                            conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN interval_minutes INTEGER DEFAULT 15;"))
                        if "max_repeats" not in cols:
                            conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN max_repeats INTEGER DEFAULT 3;"))
                        if "play_on_publish" not in cols:
                            conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN play_on_publish BOOLEAN DEFAULT 1;"))
                        if "next_repeat_at" not in cols:
                            conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN next_repeat_at DATETIME;"))
                        if "last_repeat_at" not in cols:
                            conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN last_repeat_at DATETIME;"))
                except Exception:
                    pass

                # 3. speaker_queue table
                try:
                    res = conn.execute(text("PRAGMA table_info(speaker_queue);")).fetchall()
                    cols = [r[1] for r in res]
                    if cols:
                        if "duration_seconds" not in cols:
                            conn.execute(text("ALTER TABLE speaker_queue ADD COLUMN duration_seconds INTEGER DEFAULT 15;"))
                        if "failure_reason" not in cols:
                            conn.execute(text("ALTER TABLE speaker_queue ADD COLUMN failure_reason VARCHAR(255);"))
                        if "error_count" not in cols:
                            conn.execute(text("ALTER TABLE speaker_queue ADD COLUMN error_count INTEGER DEFAULT 0;"))
                except Exception:
                    pass
            else:
                # PostgreSQL
                try:
                    conn.execute(text("ALTER TABLE announcements ADD COLUMN IF NOT EXISTS target_audience VARCHAR(255) DEFAULT 'Entire College';"))
                    conn.execute(text("ALTER TABLE announcements ADD COLUMN IF NOT EXISTS ai_summary TEXT;"))
                    conn.execute(text("ALTER TABLE announcements ADD COLUMN IF NOT EXISTS speaker_voice VARCHAR(20) DEFAULT 'female';"))
                    conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN IF NOT EXISTS repeat_mode VARCHAR(20) DEFAULT 'INTERVAL';"))
                    conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN IF NOT EXISTS interval_minutes INTEGER DEFAULT 15;"))
                    conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN IF NOT EXISTS max_repeats INTEGER DEFAULT 3;"))
                    conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN IF NOT EXISTS play_on_publish BOOLEAN DEFAULT TRUE;"))
                    conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN IF NOT EXISTS next_repeat_at TIMESTAMP WITH TIME ZONE;"))
                    conn.execute(text("ALTER TABLE announcement_repeat_schedules ADD COLUMN IF NOT EXISTS last_repeat_at TIMESTAMP WITH TIME ZONE;"))
                    conn.execute(text("ALTER TABLE speaker_queue ADD COLUMN IF NOT EXISTS duration_seconds INTEGER DEFAULT 15;"))
                    conn.execute(text("ALTER TABLE speaker_queue ADD COLUMN IF NOT EXISTS failure_reason VARCHAR(255);"))
                    conn.execute(text("ALTER TABLE speaker_queue ADD COLUMN IF NOT EXISTS error_count INTEGER DEFAULT 0;"))
                except Exception:
                    pass
    except Exception:
        pass


# Run migrations once upon module load
ensure_schema_migrations()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
