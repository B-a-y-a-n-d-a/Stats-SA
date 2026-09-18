# Implements specs/002-ingestion-pipeline/spec.md, model choice per specs/000.
from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer  # deferred: slow import

    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    return model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()
