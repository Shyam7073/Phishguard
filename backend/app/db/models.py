from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


class ScanRecord(Base):
    __tablename__ = "scan_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
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
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
