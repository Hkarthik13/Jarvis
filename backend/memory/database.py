import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.memory.models import Base
from backend.utils.logger import logger

# SQLite database file path in project root
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "jarvis_memory.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes SQLite database tables and configures WAL mode."""
    try:
        # Enable WAL mode for high performance SQLite operations
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
            conn.exec_driver_sql("PRAGMA synchronous=NORMAL;")
        Base.metadata.create_all(bind=engine)
        logger.info(f"Initialized JARVIS Memory Database at: {DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize memory database: {e}")
        raise

@contextmanager
def get_db():
    """Context manager for safe, thread-safe database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()
