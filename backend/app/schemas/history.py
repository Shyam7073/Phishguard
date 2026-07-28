from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    is_phishing: bool
    confidence: float
    scanned_at: datetime
