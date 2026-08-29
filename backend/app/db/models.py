from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


class ScanRecord(Base):
    __tablename__ = "scan_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Per-install ID the extension generates and stores in chrome.storage.local.
    # Not real auth -- just enough to keep each friend's history separate.
    client_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    is_phishing: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    # Nullable: rows scanned before Milestone 10a's URLhaus integration have none of these.
    ml_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    urlhaus_status: Mapped[str | None] = mapped_column(String, nullable=True)
    # Nullable: rows scanned before Milestone 13's RDAP domain-age integration have none of these.
    domain_age_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    domain_age_status: Mapped[str | None] = mapped_column(String, nullable=True)
    verdict_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    # timezone=True matters: the default below is an *aware* UTC datetime, and
    # a plain DateTime column silently drops the offset on the way in. Clients
    # then get an ISO string with no offset, which JavaScript's `new Date()`
    # parses as local time -- so the dashboard showed every scan shifted by the
    # viewer's UTC offset. (ScanRecordOut re-attaches UTC on the way out, for
    # rows already written to the old, offset-less column.)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
