import secrets

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central config. Every value is read from the environment (.env in local dev,
    real env vars in any deployed container) — never hardcode a secret here."""

    database_url: str = "postgresql+psycopg://statssa:statssa@localhost:5432/statssa"
    # No fixed fallback: a well-known default would let anyone mint a curator
    # token. Unset means a per-process random secret, so tokens simply stop
    # validating across restarts until JWT_SECRET is configured.
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 480

    llm_provider: str = "anthropic"  # see specs/000-mvp-technical-decisions.md
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-5"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    # 0.75 (the original docs' placeholder) was never measured against this model
    # and rejects every query, including clearly relevant ones. Live-tested with
    # all-MiniLM-L6-v2 against a real Stats SA document (specs/003): relevant
    # queries scored 0.47-0.54 cosine similarity, irrelevant ones 0.17-0.18. 0.4
    # sits comfortably in that gap. Re-calibrate as the real registry grows.
    confidence_threshold: float = 0.4

    class Config:
        env_file = ".env"


settings = Settings()
