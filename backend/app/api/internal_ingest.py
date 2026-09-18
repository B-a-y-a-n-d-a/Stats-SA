# Implements specs/002-ingestion-pipeline/spec.md — branch feature/002-ingestion-pipeline.
from fastapi import APIRouter

router = APIRouter(prefix="/internal", tags=["internal"])

# POST /internal/ingest — called by the Curator-Admin API (specs/008), not exposed publicly.
