import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import ScanRecord

router = APIRouter()


def _iso_utc(value: datetime | None) -> str:
    """Render scanned_at as an unambiguous UTC ISO-8601 string.

    Straight str() of the column gives "2026-08-29 12:36:17.211456" with no
    offset, which is ambiguous in a file meant to be opened somewhere else --
    and rows written before scanned_at became a timezone-aware column come
    back naive. Everything is written as UTC, so stamp that on explicitly.
    """
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


@router.get("/reports")
def export_reports_csv(
    client_id: str = Query(..., min_length=1), db: Session = Depends(get_db)
) -> StreamingResponse:
    records = (
        db.query(ScanRecord)
        .filter(ScanRecord.client_id == client_id)
        .order_by(desc(ScanRecord.scanned_at), desc(ScanRecord.id))
        .all()
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "client_id",
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
                record.client_id,
                record.url,
                record.is_phishing,
                record.confidence,
                record.ml_score,
                record.urlhaus_status,
                record.domain_age_days,
                record.domain_age_status,
                record.verdict_reason,
                _iso_utc(record.scanned_at),
            ]
        )
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=phishguard_report.csv"},
    )
