# Implements specs/003-retrieval-confidence-gate/spec.md, pluggable per specs/000
# ("a pluggable LLMClient interface, defaulting to a hosted API for the demo").
from abc import ABC, abstractmethod

from app.core.config import settings


class LLMClient(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Returns the raw model response text."""


class AnthropicLLMClient(LLMClient):
    """Requires LLM_API_KEY set in the environment (.env). Not exercised by the
    live-testing done for this task — no API key is available in the build
    environment. The retrieval/confidence/citation mechanism this task actually
    verifies is tested against a fake client instead; this class is the real
    wiring for whoever runs it with a key."""

    def __init__(self):
        import anthropic  # deferred: optional dependency, only needed if selected

        self._client = anthropic.Anthropic(api_key=settings.llm_api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.messages.create(
            model=settings.llm_model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text


def get_llm_client() -> LLMClient:
    if settings.llm_provider == "anthropic":
        return AnthropicLLMClient()
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
