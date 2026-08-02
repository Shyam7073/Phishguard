from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import ScanRecord
from backend.app.ml_service.predictor import predict
from backend.app.schemas.scan import ScanRequest, ScanResponse
from backend.app.threat_intel.domain_age import check_domain_age
from backend.app.threat_intel.urlhaus import check_urlhaus
from backend.app.verdict import combine_verdict

router = APIRouter()


@router.post("/scan", response_model=ScanResponse)
async def scan_url(request: ScanRequest, db: Session = Depends(get_db)) -> ScanResponse:
    ml_result = predict(request.url)
    urlhaus_status = await check_urlhaus(request.url)
    domain_age = await check_domain_age(request.url)
    verdict = combine_verdict(
        ml_result["phishing_probability"], urlhaus_status, domain_age["domain_age_status"]
    )

    db.add(
        ScanRecord(
            url=request.url,
            is_phishing=verdict["is_phishing"],
            confidence=verdict["confidence"],
            ml_score=ml_result["phishing_probability"],
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
        ml_score=ml_result["phishing_probability"],
        urlhaus_status=urlhaus_status,
        domain_age_days=domain_age["domain_age_days"],
        domain_age_status=domain_age["domain_age_status"],
        verdict_reason=verdict["verdict_reason"],
    )
