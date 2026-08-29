from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import ScanRecord
from backend.app.schemas.history import ScanRecordOut

router = APIRouter()


@router.get("/history", response_model=list[ScanRecordOut])
def get_history(
    client_id: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[ScanRecord]:
    # id is a tiebreaker, not decoration: the extension routinely fires
    # several scans inside one clock tick (a page load plus its redirects),
    # and `scanned_at` alone leaves those rows in an arbitrary order -- so
    # the LIMIT could drop a newer row and keep an older one from the same
    # timestamp, and the same query could return a different page twice.
    return (
        db.query(ScanRecord)
        .filter(ScanRecord.client_id == client_id)
        .order_by(desc(ScanRecord.scanned_at), desc(ScanRecord.id))
        .limit(limit)
        .all()
    )
