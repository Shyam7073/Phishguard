"""Engine/session setup.

Uses Postgres (Neon) via DATABASE_URL when set -- this is required for
deployment, since free hosts like Render wipe local disk (and any SQLite
file on it) on every restart/idle spin-down. Falls back to a local SQLite
file for offline dev when DATABASE_URL isn't set.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
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
