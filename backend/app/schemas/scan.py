from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    url: str = Field(..., min_length=1, examples=["http://example.com"])
    client_id: str = Field(..., min_length=1, description="Per-install ID from the extension")


class ScanResponse(BaseModel):
    url: str
    is_phishing: bool
    confidence: float
    ml_score: float | None = Field(
        ...,
        description=(
            "Raw phishing probability from the ML model, or null if not run (e.g. trusted host)"
        ),
    )
    urlhaus_status: str | None = Field(
        ..., description="'listed', 'not_listed', 'unknown', or null if not checked"
    )
    domain_age_days: int | None = Field(
        ..., description="Domain age in days per RDAP, or null if unavailable"
    )
    domain_age_status: str | None = Field(
        ..., description="'new', 'moderate', 'established', 'unknown', or null if not checked"
    )
    verdict_reason: str
