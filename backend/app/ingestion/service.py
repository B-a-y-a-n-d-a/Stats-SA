# Implements specs/002-ingestion-pipeline/spec.md.
#
# Re-ingesting the same source (same url) never edits a row in place: it always
# creates a new version and sets superseded_by on the prior one, matching the
# Approved Sources Registry versioning rule in docs/02-architecture.md Section 4.
import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.db.models import Chunk, Source, SourceCategory
from app.ingestion.chunker import chunk_text
from app.ingestion.embedder import embed_texts
from app.ingestion.parser import compute_checksum, parse_pdf


def ingest_source(
    db: Session,
    *,
    file_bytes: bytes,
    title: str,
    url: str,
    category: SourceCategory,
    published_date: date,
    approved_by=None,
) -> Source:
    checksum = compute_checksum(file_bytes)

    existing = (
        db.query(Source)
        .filter(Source.url == url, Source.superseded_by.is_(None))
        .order_by(Source.version.desc())
        .first()
    )
    if existing and existing.checksum == checksum:
        return existing  # identical content already ingested — nothing to do

    version = (existing.version + 1) if existing else 1

    pages = parse_pdf(file_bytes)
    chunk_dicts = chunk_text(pages)
    embeddings = embed_texts([c["text"] for c in chunk_dicts])

    new_source = Source(
        source_id=uuid.uuid4(),
        title=title,
        url=url,
        category=category,
        published_date=published_date,
        ingested_date=datetime.utcnow(),
        version=version,
        approved_by=approved_by,
        checksum=checksum,
    )
    db.add(new_source)
    db.flush()  # assigns new_source.source_id before chunks reference it

    for c, emb in zip(chunk_dicts, embeddings):
        db.add(
            Chunk(
                chunk_id=uuid.uuid4(),
                source_id=new_source.source_id,
                text=c["text"],
                embedding=emb,
                page_number=c["page_number"],
                char_start=c["char_start"],
                char_end=c["char_end"],
            )
        )

    if existing:
        existing.superseded_by = new_source.source_id

    db.commit()
    db.refresh(new_source)
    return new_source
