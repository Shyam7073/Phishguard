import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.api.scan as scan_module
from backend.app.db.database import Base, get_db
from backend.app.main import app

# In-memory SQLite for tests -- StaticPool keeps every session on the same
# connection, otherwise each new session would get its own empty in-memory
# database and never see data written by a previous request.
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(monkeypatch):
    Base.metadata.create_all(bind=TEST_ENGINE)
    app.dependency_overrides[get_db] = _override_get_db

    # Default to "not_listed" so tests never make a real network call to
    # URLhaus; tests that care about the blocklisted/unknown paths override
    # scan_module.check_urlhaus themselves via monkeypatch.
    async def _fake_not_listed(url: str) -> str:
        return "not_listed"

    monkeypatch.setattr(scan_module, "check_urlhaus", _fake_not_listed)

    # Default to "unknown" (no RDAP data) so tests never make a real network
    # call for domain age either; tests that care about the new/established
    # paths override scan_module.check_domain_age themselves via monkeypatch.
    async def _fake_domain_age_unknown(url: str) -> dict:
        return {"domain_age_days": None, "domain_age_status": "unknown"}

    monkeypatch.setattr(scan_module, "check_domain_age", _fake_domain_age_unknown)

    yield TestClient(app)

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=TEST_ENGINE)
