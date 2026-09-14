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
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
elif DATABASE_URL.startswith("sqlite:///") and (":memory:" not in DATABASE_URL):
    raw_path = DATABASE_URL.replace("sqlite:///", "")
    if not os.path.isabs(raw_path):
        DATABASE_URL = f"sqlite:///{canonical_db_path}"

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

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
