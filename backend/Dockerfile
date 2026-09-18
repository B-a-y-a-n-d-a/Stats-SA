# Build context is the repo root (infra/docker-compose.yml), not this
# directory — this container also needs demo/seed-data-for-demo/ (specs/011),
# which lives outside backend/, for the pre-seeded demo document. Every COPY
# below is therefore rooted at the repo root, not at backend/.
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
# sentence-transformers (app/ingestion/embedder.py) pulls in torch, and
# without this, pip resolves the default PyPI torch wheel — the full CUDA
# build, which drags in triton + several nvidia-* packages totalling 1GB+
# this container (CPU-only, no GPU) will never use. Found live bringing up
# docker-compose for specs/011: that huge download intermittently failed
# pip's hash verification against PyPI, and even when it succeeded the image
# was enormous. Installing the CPU-only build first satisfies
# sentence-transformers' torch requirement before it gets a chance to
# resolve the CUDA one.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
# scripts/ingest_seed_set.py resolves each entry's local_path against
# BACKEND_ROOT (= /app here), so a path like "../demo/seed-data-for-demo/x.pdf"
# needs /demo to exist as a sibling of /app — matching the repo's own layout.
COPY demo/ /demo/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
