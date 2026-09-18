# Implements specs/003-retrieval-confidence-gate/spec.md.
# Default threshold 0.75 per docs/05-mvp-scope-and-roadmap.md, overridable via
# CONFIDENCE_THRESHOLD (app/core/config.py).
from app.core.config import settings


def compute_confidence(results: list[dict]) -> float:
    if not results:
        return 0.0
    return float(results[0]["similarity"])


def clears_threshold(confidence: float) -> bool:
    return confidence >= settings.confidence_threshold
