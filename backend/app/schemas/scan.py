from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    url: str = Field(..., min_length=1, examples=["http://example.com"])


class ScanResponse(BaseModel):
    url: str
    is_phishing: bool
    confidence: float
