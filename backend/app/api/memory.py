# Implements specs/007-communication-memory/spec.md — branch feature/007-communication-memory.
from fastapi import APIRouter

router = APIRouter(prefix="/api/memory", tags=["memory"])

# GET /api/memory/search?q=
