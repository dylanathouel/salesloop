"""Paragraph-aware chunking of training documents.

Paragraphs are grouped up to `max_chars`; oversized paragraphs are
hard-split with an overlap so no context is lost at boundaries.
"""

DEFAULT_MAX_CHARS = 1200
DEFAULT_OVERLAP = 150


def _split_long_text(text: str, max_chars: int, overlap: int) -> list[str]:
    pieces = []
    start = 0
    while start < len(text):
        pieces.append(text[start : start + max_chars].strip())
        start += max_chars - overlap
    return [p for p in pieces if p]


def chunk_text(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Split a document into retrieval-sized chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_text(paragraph, max_chars, overlap))
            continue
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)

    return chunks
