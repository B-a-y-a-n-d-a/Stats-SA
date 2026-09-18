# Implements specs/003-retrieval-confidence-gate/spec.md.
#
# Only current-version sources are retrievable: a superseded source's chunks
# are excluded, matching docs/02-architecture.md Section 4 ("retrieval always
# prefers the current version"). A retired source (specs/008-curator-admin —
# DELETE /api/curator/sources/{id} sets Source.retired_at) is excluded the
# same way: retirement marks it non-retrievable without hard-deleting it.
from sqlalchemy.orm import Session

from app.db.models import Chunk, Source
from app.ingestion.embedder import embed_texts


def search_chunks(db: Session, query_text: str, top_k: int = 5) -> list[dict]:
    query_embedding = embed_texts([query_text])[0]
    distance = Chunk.embedding.cosine_distance(query_embedding)

    rows = (
        db.query(Chunk, Source, distance.label("distance"))
        .join(Source, Chunk.source_id == Source.source_id)
        .filter(Source.superseded_by.is_(None))
        .filter(Source.retired_at.is_(None))
        .order_by(distance)
        .limit(top_k)
        .all()
    )

    results = []
    for chunk, source, distance_val in rows:
        results.append(
            {
                "chunk_id": chunk.chunk_id,
                "source_id": source.source_id,
                "text": chunk.text,
                "title": source.title,
                "url": source.url,
                "published_date": source.published_date,
                "similarity": 1 - distance_val,  # cosine distance -> similarity
            }
        )
    return results
