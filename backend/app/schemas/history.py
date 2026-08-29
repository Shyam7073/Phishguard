from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_validator


class ScanRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    is_phishing: bool
    confidence: float
    ml_score: float | None = None
    urlhaus_status: str | None = None
    domain_age_days: int | None = None
    domain_age_status: str | None = None
    verdict_reason: str | None = None
    scanned_at: datetime

    @field_validator("scanned_at")
    @classmethod
    def _assume_utc(cls, value: datetime) -> datetime:
        """Stamp UTC onto naive timestamps.

        Everything is written as `datetime.now(timezone.utc)`, but rows stored
        before `scanned_at` became a timezone-aware column come back without an
        offset. Serialised that way, `new Date(...)` in the dashboard reads them
        as local time and shows every scan shifted by the viewer's UTC offset.
        """
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
