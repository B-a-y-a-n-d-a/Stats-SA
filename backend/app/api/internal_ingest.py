# Implements specs/002-ingestion-pipeline/spec.md.
# Called by the Curator-Admin API (specs/008), not exposed publicly.
from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db.models import SourceCategory
from app.db.session import get_db
from app.ingestion.service import ingest_source

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/ingest")
async def ingest(
    title: str = Form(...),
    url: str = Form(...),
    category: SourceCategory = Form(...),
    published_date: date = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()
    source = ingest_source(
        db,
        file_bytes=file_bytes,
        title=title,
        url=url,
        category=category,
        published_date=published_date,
    )
    return {"source_id": str(source.source_id), "version": source.version}
