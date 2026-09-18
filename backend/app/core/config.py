from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central config. Every value is read from the environment (.env in local dev,
    real env vars in any deployed container) — never hardcode a secret here."""

    database_url: str = "postgresql+psycopg://statssa:statssa@localhost:5432/statssa"
    jwt_secret: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 480

    llm_provider: str = "anthropic"  # see specs/000-mvp-technical-decisions.md
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-5"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    confidence_threshold: float = 0.75

    class Config:
        env_file = ".env"


settings = Settings()
