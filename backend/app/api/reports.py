import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import ScanRecord

router = APIRouter()


@router.get("/reports")
def export_reports_csv(db: Session = Depends(get_db)) -> StreamingResponse:
    records = db.query(ScanRecord).order_by(desc(ScanRecord.scanned_at)).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "url",
            "is_phishing",
            "confidence",
            "ml_score",
            "urlhaus_status",
            "domain_age_days",
            "domain_age_status",
            "verdict_reason",
            "scanned_at",
        ]
    )
    for record in records:
        writer.writerow(
            [
                record.id,
                record.url,
                record.is_phishing,
                record.confidence,
                record.ml_score,
                record.urlhaus_status,
                record.domain_age_days,
                record.domain_age_status,
                record.verdict_reason,
                record.scanned_at,
            ]
        )
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=phishguard_report.csv"},
    )
