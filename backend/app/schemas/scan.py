from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    url: str = Field(..., min_length=1, examples=["http://example.com"])


class ScanResponse(BaseModel):
    url: str
    is_phishing: bool
    confidence: float
    ml_score: float = Field(..., description="Raw phishing probability from the ML model alone")
    urlhaus_status: str = Field(..., description="'listed', 'not_listed', or 'unknown'")
    domain_age_days: int | None = Field(
        ..., description="Domain age in days per RDAP, or null if unavailable"
    )
    domain_age_status: str = Field(
        ..., description="'new', 'moderate', 'established', or 'unknown'"
    )
    verdict_reason: str
