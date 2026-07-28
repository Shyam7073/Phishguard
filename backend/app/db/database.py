"""SQLite engine/session setup.

Using SQLAlchemy as the ORM means the only change needed to move to
Postgres later is swapping this connection string -- nothing in the models
or route handlers is SQLite-specific.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DB_PATH = Path(__file__).resolve().parents[2] / "phishguard.db"

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session, closes it after the request."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
