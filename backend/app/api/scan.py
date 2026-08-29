from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import ScanRecord
from backend.app.demo import DEMO_CLIENT_ID
from backend.app.ml_service.predictor import predict
from backend.app.schemas.scan import ScanRequest, ScanResponse
from backend.app.threat_intel.domain_age import check_domain_age
from backend.app.threat_intel.urlhaus import check_urlhaus
from backend.app.trusted_hosts import is_trusted_host
from backend.app.verdict import combine_verdict

router = APIRouter()

TRUSTED_HOST_VERDICT = {
    "is_phishing": False,
    "confidence": 1.0,
    "verdict_reason": "Trusted PhishGuard host",
}


@router.post("/scan", response_model=ScanResponse)
async def scan_url(request: ScanRequest, db: Session = Depends(get_db)) -> ScanResponse:
    # The demo history is a fixed, seeded showcase for anyone opening the
    # dashboard without the extension -- real traffic must not append to it.
    if request.client_id == DEMO_CLIENT_ID:
        raise HTTPException(status_code=403, detail=f"'{DEMO_CLIENT_ID}' is a reserved client_id")

    hostname = urlparse(request.url).hostname

    if is_trusted_host(hostname):
        verdict = TRUSTED_HOST_VERDICT
        ml_score = None
        urlhaus_status = None
        domain_age = {"domain_age_days": None, "domain_age_status": None}
    else:
        ml_result = predict(request.url)
        urlhaus_status = await check_urlhaus(request.url)
        domain_age = await check_domain_age(request.url)
        verdict = combine_verdict(
            ml_result["phishing_probability"], urlhaus_status, domain_age["domain_age_status"]
        )
        ml_score = ml_result["phishing_probability"]

    db.add(
        ScanRecord(
            client_id=request.client_id,
            url=request.url,
            is_phishing=verdict["is_phishing"],
            confidence=verdict["confidence"],
            ml_score=ml_score,
            urlhaus_status=urlhaus_status,
            domain_age_days=domain_age["domain_age_days"],
            domain_age_status=domain_age["domain_age_status"],
            verdict_reason=verdict["verdict_reason"],
        )
    )
    db.commit()

    return ScanResponse(
        url=request.url,
        is_phishing=verdict["is_phishing"],
        confidence=verdict["confidence"],
        ml_score=ml_score,
        urlhaus_status=urlhaus_status,
        domain_age_days=domain_age["domain_age_days"],
        domain_age_status=domain_age["domain_age_status"],
        verdict_reason=verdict["verdict_reason"],
    )
