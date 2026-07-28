from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import ScanRecord
from backend.app.ml_service.predictor import predict
from backend.app.schemas.scan import ScanRequest, ScanResponse

router = APIRouter()


@router.post("/scan", response_model=ScanResponse)
def scan_url(request: ScanRequest, db: Session = Depends(get_db)) -> ScanResponse:
    result = predict(request.url)

    db.add(ScanRecord(url=request.url, **result))
    db.commit()

    return ScanResponse(url=request.url, **result)
