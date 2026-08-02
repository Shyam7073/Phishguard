from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
