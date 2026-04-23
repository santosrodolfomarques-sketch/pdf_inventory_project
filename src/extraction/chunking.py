from __future__ import annotations

def chunk_text(text: str, max_chars: int, overlap: int = 0) -> list[str]:
    text = text or ""
    if len(text) <= max_chars:
        return [text] if text else []

    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + max_chars, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= text_length:
            break
        start = max(0, end - overlap)

    return chunks
