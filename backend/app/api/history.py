from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import ScanRecord
from backend.app.schemas.history import ScanRecordOut

router = APIRouter()


@router.get("/history", response_model=list[ScanRecordOut])
def get_history(
    limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)
) -> list[ScanRecord]:
    return db.query(ScanRecord).order_by(desc(ScanRecord.scanned_at)).limit(limit).all()
