"""Engine/session setup.

Uses Postgres (Neon) via DATABASE_URL when set -- this is required for
deployment, since free hosts like Render wipe local disk (and any SQLite
file on it) on every restart/idle spin-down. Falls back to a local SQLite
file for offline dev when DATABASE_URL isn't set.

Guard against developing against the live database
--------------------------------------------------
DATABASE_URL lives in `.env` on the dev machine (it is needed there to run
`seed_demo.py --deployed`), and `.env` is gitignored so it never ships. That
combination used to make `uvicorn` on localhost silently write real rows into
the deployed Neon database: `load_dotenv()` picks the URL up, and nothing
distinguished "I am the deployment" from "I am a laptop that happens to hold
the deployment's credential".

The distinguishing fact is the `.env` file itself. It exists only on a dev
machine; the deployment gets DATABASE_URL from Render's own environment and
has no `.env` at all. So a remote URL that arrives while a `.env` file is
present is treated as a dev machine holding a production credential, and the
engine falls back to local SQLite instead of honouring it. Opt back in with
PHISHGUARD_DEPLOYED=1 when writing to the deployed database is the actual
intent -- the same explicit-confirmation rule `seed_demo.py` already applies
via its `--deployed` flag.

Nothing here requires configuration on Render: with no `.env` in the
deployment, the guard never engages.
"""

import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
DB_PATH = Path(__file__).resolve().parents[2] / "phishguard.db"

# A URL that is not SQLite is remote, i.e. the deployed Neon database.
_is_remote = bool(DATABASE_URL) and not DATABASE_URL.startswith("sqlite")
# find_dotenv() with no argument resolves from this file's directory upward,
# which is exactly how the load_dotenv() call above located the file -- using
# usecwd=True here instead would disagree with it whenever the server is
# started from a different working directory, and silently unlock the
# deployed database.
_on_dev_machine = bool(find_dotenv())
_opted_in = os.environ.get("PHISHGUARD_DEPLOYED", "").lower() in {"1", "true", "yes"}

USING_DEPLOYED_DB = _is_remote and (not _on_dev_machine or _opted_in)

if _is_remote and not USING_DEPLOYED_DB:
    print(
        "WARNING: DATABASE_URL points at a remote database but a local .env "
        "file is present, so this looks like a dev machine. Using local SQLite "
        f"({DB_PATH.name}) instead, to keep development traffic out of the "
        "deployed database. Set PHISHGUARD_DEPLOYED=1 to override."
    )

if USING_DEPLOYED_DB:
    engine = create_engine(DATABASE_URL)
elif DATABASE_URL and not _is_remote:
    # An explicitly-supplied SQLite URL (used by tests).
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
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
