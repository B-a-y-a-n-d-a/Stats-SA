# Implements specs/003-retrieval-confidence-gate/spec.md, pluggable per specs/000
# ("a pluggable LLMClient interface, defaulting to a hosted API for the demo").
import json
import re
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


class FakeLLMClient(LLMClient):
    """Selected via LLM_PROVIDER=fake (.env) — no network call, no API key.

    This is a demo-resilience fallback, not the normal way to demo: it exists
    because specs/011's own Risk Register (docs/05-mvp-scope-and-roadmap.md,
    "Demo-day connectivity failure... run the demo against a local build")
    calls for a way to run the full script without depending on a live LLM API
    on the day, and so a teammate without an LLM_API_KEY can still run the
    whole stack locally. The default LLM_PROVIDER remains "anthropic" — flip
    to "fake" only as the documented fallback (see demo/run-demo.md), never as
    the first choice for an actual judged demo.

    It is not a stub that fabricates content: it parses the *real* retrieved
    excerpts straight out of the prompt this module builds
    (service.py's _build_user_prompt: 'chunk_id: <uuid>\\nsource: <title>\\n
    text: \"\"\"<text>\"\"\"') and returns an answer citing the first excerpt
    with a quote lifted verbatim from its own text — so the real citation
    enforcement in app/retrieval/citation.py still verifies it against actual
    chunk content, same as it would a real model's response.
    """

    _EXCERPT_RE = re.compile(r'chunk_id: (\S+)\s*\nsource: .*?\ntext: """(.*?)"""', re.DOTALL)
    _MIN_QUOTE_LINE_LEN = 30  # see _pick_quote_line
    _MAX_QUOTE_LEN = 120
    # Common government-document letterhead/contact markers — found live-testing
    # against a real Stats SA media release, whose chunk 1 opens with a postal
    # address ('Private Bag X44, Pretoria, 0001, South Africa, ISIbalo House,
    # Koch Street, Salvokop, Pretoria, 0002' — 100+ characters, so a plain
    # minimum-length check alone doesn't skip it) three lines above the actual
    # finding. Matched case-insensitively against each line.
    _BOILERPLATE_MARKERS = (
        "private bag", "tel:", "tel.", "cell:", "email:", "www.", "@",
        "embargo:", "media release", "issued by",
    )

    @classmethod
    def _pick_quote_line(cls, text: str) -> str:
        """Skip letterhead/contact-style lines in favor of the first
        substantive one, so the demo cites an actual finding instead of a
        postal address. This is a marker-based heuristic, not real language
        understanding — on the QLFS media release it lands on the document's
        title line ("Quarterly Labour Force Survey (QLFS) - Q2: 2026"), one
        line above the actual figure. That's an acceptable outcome for an
        emergency fallback (true, verbatim, not embarrassing) but not a
        claim that this picks the *best* line — good enough here precisely
        because LLM_PROVIDER=anthropic is the real answer-quality path."""
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        if not lines:
            return ""

        def is_boilerplate(line: str) -> bool:
            lowered = line.lower()
            return len(line) < cls._MIN_QUOTE_LINE_LEN or any(marker in lowered for marker in cls._BOILERPLATE_MARKERS)

        return next((line for line in lines if not is_boilerplate(line)), lines[0])

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        match = self._EXCERPT_RE.search(user_prompt)
        if not match:
            return json.dumps({"answer": None, "citations": []})
        chunk_id, text = match.group(1), match.group(2)
        quote = self._pick_quote_line(text)[: self._MAX_QUOTE_LEN].strip()
        if not quote:
            return json.dumps({"answer": None, "citations": []})
        return json.dumps(
            {
                "answer": f"Based on the retrieved source material: {quote}",
                "citations": [{"chunk_id": chunk_id, "quote": quote}],
            }
        )


def get_llm_client() -> LLMClient:
    if settings.llm_provider == "anthropic":
        return AnthropicLLMClient()
    if settings.llm_provider == "fake":
        return FakeLLMClient()
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
