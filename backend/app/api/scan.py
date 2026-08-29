import asyncio
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import ScanRecord
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
    hostname = urlparse(request.url).hostname

    if is_trusted_host(hostname):
        verdict = TRUSTED_HOST_VERDICT
        ml_score = None
        urlhaus_status = None
        domain_age = {"domain_age_days": None, "domain_age_status": None}
    else:
        # The three signals are independent, so run them concurrently. Run
        # sequentially the two lookups stack their 4s timeouts, making a
        # single slow scan take 8s+; ML inference goes through a thread so
        # the (synchronous, CPU-bound) model call doesn't block the event
        # loop while the two HTTP lookups are in flight.
        ml_result, urlhaus_status, domain_age = await asyncio.gather(
            asyncio.to_thread(predict, request.url),
            check_urlhaus(request.url),
            check_domain_age(request.url),
        )
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
