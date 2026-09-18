from fastapi import FastAPI

from app.api import (
    audit,
    auth,
    curator,
    internal_ingest,
    media_query,
    memory,
    public_query,
    review,
)

app = FastAPI(
    title="Stats SA AI-Enabled Assistant",
    description="GovTech 2026 hackathon MVP. See docs/ and specs/ for the design and build plan.",
)


@app.get("/health")
def health():
    return {"status": "ok"}


# Every feature branch owns one router file in app/api/ and does NOT need to edit this
# file to register it — routers are already wired here as part of the project scaffold.
app.include_router(public_query.router)
app.include_router(media_query.router)
app.include_router(review.router)
app.include_router(memory.router)
app.include_router(curator.router)
app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(internal_ingest.router)
