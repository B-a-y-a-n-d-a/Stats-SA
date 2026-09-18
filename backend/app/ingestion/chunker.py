# Implements specs/002-ingestion-pipeline/spec.md.
#
# Target ~300-500 tokens per chunk (approximated as ~1600 chars). A [Table]...[/Table]
# block from parser.py is never split mid-table, so a statistical table's rows
# always stay together in one chunk.
import re

from app.ingestion.parser import ParsedPage

TARGET_CHARS = 1600
_TABLE_SPLIT = re.compile(r"(\[Table\].*?\[/Table\])", re.DOTALL)


def _make_chunk(text: str, page_number: int, char_start: int, char_end: int) -> dict:
    return {
        "text": text.strip(),
        "page_number": page_number,
        "char_start": char_start,
        "char_end": char_end,
    }


def chunk_text(pages: list[ParsedPage]) -> list[dict]:
    chunks: list[dict] = []
    for page in pages:
        cursor = 0
        buffer = ""
        buffer_start = 0
        for part in _TABLE_SPLIT.split(page.text):
            if not part.strip():
                cursor += len(part)
                continue
            if part.startswith("[Table]"):
                if buffer.strip():
                    chunks.append(_make_chunk(buffer, page.page_number, buffer_start, cursor))
                    buffer = ""
                chunks.append(_make_chunk(part, page.page_number, cursor, cursor + len(part)))
            else:
                if not buffer:
                    buffer_start = cursor
                buffer += part
                while len(buffer) >= TARGET_CHARS:
                    split_at = buffer.rfind(". ", 0, TARGET_CHARS)
                    split_at = split_at + 1 if split_at != -1 else TARGET_CHARS
                    chunks.append(
                        _make_chunk(buffer[:split_at], page.page_number, buffer_start, buffer_start + split_at)
                    )
                    buffer = buffer[split_at:]
                    buffer_start += split_at
            cursor += len(part)
        if buffer.strip():
            chunks.append(_make_chunk(buffer, page.page_number, buffer_start, cursor))
    return [c for c in chunks if c["text"]]
