"""Bulk-ingests the curated Stats SA source set. specs/002-ingestion-pipeline.

Run with: python -m scripts.ingest_seed_set   (from the backend/ directory)

Add more entries to seed_sources.yaml as the team curates the 15-30 document
set (specs/000, docs/05-mvp-scope-and-roadmap.md).
"""
from pathlib import Path

import httpx
import yaml

from app.db.models import SourceCategory
from app.db.session import SessionLocal
from app.ingestion.service import ingest_source

CONFIG_PATH = Path(__file__).parent / "seed_sources.yaml"
BACKEND_ROOT = Path(__file__).parent.parent


def _load_bytes(entry: dict) -> bytes:
    local_path = entry.get("local_path")
    if local_path:
        return (BACKEND_ROOT / local_path).read_bytes()
    resp = httpx.get(entry["url"], timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


def main():
    entries = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        for entry in entries:
            print(f"Ingesting: {entry['title']}")
            file_bytes = _load_bytes(entry)
            source = ingest_source(
                db,
                file_bytes=file_bytes,
                title=entry["title"],
                url=entry["url"],
                category=SourceCategory(entry["category"]),
                published_date=entry["published_date"],
            )
            print(f"  -> source_id={source.source_id} version={source.version}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
