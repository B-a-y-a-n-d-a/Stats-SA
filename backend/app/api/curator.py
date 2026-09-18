# Implements specs/008-curator-admin/spec.md — branch feature/008-curator-admin.
#
# The only role that can change what the assistant is allowed to know. Every endpoint
# below is gated with Depends(require_role("curator_admin")) — no other role, unlike
# audit.py's two-role gate (spec: "Only the curator_admin role can call these
# endpoints -- enforce server-side").
#
# POST   /api/curator/sources           — upload a PDF or paste a URL; calls the real
#                                          ingestion service (specs/002), which already
#                                          handles versioning (same url + new checksum
#                                          -> new version, old row superseded) and is
#                                          idempotent on identical content.
# GET    /api/curator/sources           — list all sources (active/superseded/retired).
# DELETE /api/curator/sources/{id}      — retires a source: sets retired_at rather than
#                                          hard-deleting it (audit requirements). A
#                                          retired source is excluded from retrieval by
#                                          app/retrieval/search.py. Idempotent.
# GET|POST /api/curator/terminology     — list/create+version entries in
#                                          terminology_guide. MVP note (specs/000,
#                                          specs/008): a curator_admin authors an entry
#                                          alone here; the schema's approval fields exist
#                                          but dual-control (Communications Official
#                                          sign-off) enforcement is a roadmap item, not
#                                          implemented by this endpoint — the frontend
#                                          must label entries as "not yet dual-approved"
#                                          so this isn't presented as more governed than
#                                          it is.
#
# This router replaces the old, unauthenticated POST /internal/ingest
# (app/api/internal_ingest.py, deleted by this task): that endpoint duplicated
# ingestion with no auth at all, which became a real security hole once this gated
# path existed. Nothing else in the codebase called it over HTTP —
# backend/scripts/ingest_seed_set.py calls ingest_source() directly, in-process.
import uuid
from datetime import date, datetime

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.audit import log_event
from app.core.security import CurrentUser, require_role
from app.db.models import Source, SourceCategory, TerminologyCategory, TerminologyGuide
from app.db.session import get_db
from app.ingestion.service import ingest_source

router = APIRouter(prefix="/api/curator", tags=["curator"])


class TerminologyCreateRequest(BaseModel):
    category: TerminologyCategory
    term_or_topic: str
    approved_guidance: str
    discouraged_alternative: str | None = None
    rationale: str
    effective_date: date | None = None


def _serialize_source(source: Source) -> dict:
    return {
        "source_id": str(source.source_id),
        "title": source.title,
        "url": source.url,
        "category": source.category.value,
        "published_date": source.published_date.isoformat(),
        "ingested_date": source.ingested_date.isoformat(),
        "version": source.version,
        "superseded_by": str(source.superseded_by) if source.superseded_by else None,
        "retired_at": source.retired_at.isoformat() if source.retired_at else None,
        "confidentiality_tag": source.confidentiality_tag.value,
    }


def _serialize_terminology(entry: TerminologyGuide) -> dict:
    return {
        "guide_entry_id": str(entry.guide_entry_id),
        "category": entry.category.value,
        "term_or_topic": entry.term_or_topic,
        "approved_guidance": entry.approved_guidance,
        "discouraged_alternative": entry.discouraged_alternative,
        "rationale": entry.rationale,
        "version": entry.version,
        "superseded_by": str(entry.superseded_by) if entry.superseded_by else None,
        "approved_by": str(entry.approved_by) if entry.approved_by else None,
        "effective_date": entry.effective_date.isoformat(),
        "last_reviewed_date": entry.last_reviewed_date.isoformat() if entry.last_reviewed_date else None,
    }


@router.post("/sources")
async def upload_source(
    title: str = Form(...),
    url: str = Form(...),
    category: SourceCategory = Form(...),
    published_date: date = Form(...),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("curator_admin")),
):
    if file is not None:
        file_bytes = await file.read()
    else:
        # No file uploaded — url is the canonical identity URL AND where we fetch the
        # PDF bytes from, same pattern as scripts/ingest_seed_set.py's _load_bytes.
        try:
            resp = httpx.get(url, timeout=30, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError:
            raise HTTPException(status_code=400, detail="Could not fetch a file from the given URL.")
        file_bytes = resp.content

    # A 200 response isn't necessarily a PDF — e.g. a site's bot-protection layer
    # can return an HTML challenge page with a 200 status (hit live against a real
    # statssa.gov.za URL: Incapsula returned a 200 HTML page for a plain httpx GET).
    # Catch that before it reaches the parser as an unhandled 500.
    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The provided file is not a valid PDF.")

    source = ingest_source(
        db,
        file_bytes=file_bytes,
        title=title,
        url=url,
        category=category,
        published_date=published_date,
        approved_by=uuid.UUID(user.user_id),
    )

    log_event(
        "source_ingested",
        actor_id=uuid.UUID(user.user_id),
        source_id=source.source_id,
        payload={"title": title, "version": source.version},
    )

    return {"source_id": str(source.source_id), "version": source.version, "title": source.title}


@router.get("/sources")
def list_sources(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role("curator_admin")),
):
    sources = db.query(Source).order_by(Source.ingested_date.desc()).all()
    return [_serialize_source(s) for s in sources]


@router.delete("/sources/{source_id}")
def retire_source(
    source_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("curator_admin")),
):
    try:
        source_uuid = uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Source not found.")

    source = db.get(Source, source_uuid)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")

    if source.retired_at is not None:
        # Already retired — idempotent, not an error.
        return {"source_id": str(source.source_id), "retired_at": source.retired_at.isoformat()}

    source.retired_at = datetime.utcnow()
    db.commit()

    log_event(
        "source_retired",
        actor_id=uuid.UUID(user.user_id),
        source_id=source.source_id,
        payload={"title": source.title},
    )

    return {"source_id": str(source.source_id), "retired_at": source.retired_at.isoformat()}


@router.get("/terminology")
def list_terminology(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role("curator_admin")),
):
    entries = db.query(TerminologyGuide).order_by(TerminologyGuide.term_or_topic.asc()).all()
    return [_serialize_terminology(e) for e in entries]


@router.post("/terminology")
def create_terminology(
    payload: TerminologyCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("curator_admin")),
):
    existing = (
        db.query(TerminologyGuide)
        .filter(
            TerminologyGuide.superseded_by.is_(None),
            TerminologyGuide.term_or_topic.ilike(payload.term_or_topic),
        )
        .order_by(TerminologyGuide.version.desc())
        .first()
    )
    new_version = (existing.version + 1) if existing else 1

    entry = TerminologyGuide(
        guide_entry_id=uuid.uuid4(),
        category=payload.category,
        term_or_topic=payload.term_or_topic,
        approved_guidance=payload.approved_guidance,
        discouraged_alternative=payload.discouraged_alternative,
        rationale=payload.rationale,
        version=new_version,
        approved_by=uuid.UUID(user.user_id),
        effective_date=payload.effective_date or date.today(),
    )
    db.add(entry)
    db.flush()  # assigns entry.guide_entry_id before it's referenced as superseded_by

    if existing:
        existing.superseded_by = entry.guide_entry_id

    db.commit()
    db.refresh(entry)

    log_event(
        "terminology_entry_created",
        actor_id=uuid.UUID(user.user_id),
        payload={"term_or_topic": entry.term_or_topic, "version": entry.version},
    )

    return _serialize_terminology(entry)
