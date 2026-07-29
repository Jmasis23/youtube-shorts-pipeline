"""Small shared helpers: LLM JSON parsing, text chunking, timestamps."""

import json
import re


def parse_json_response(raw: str) -> dict:
    """Extract a JSON object from an LLM response.

    Models wrap JSON in prose, fenced code blocks, or both. This strips the
    fence, takes the outermost {...} span, and parses it. Raises ValueError
    with a truncated echo of the response when nothing parses, so callers can
    surface something actionable instead of a bare JSONDecodeError.
    """
    text = (raw or "").strip()

    if "```" in text:
        # Take the contents of the first fenced block.
        parts = text.split("```")
        if len(parts) >= 2:
            block = parts[1]
            if block.lstrip().lower().startswith("json"):
                block = block.lstrip()[4:]
            text = block.strip()

    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError(f"No JSON object in LLM response: {raw[:300]!r}")

    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON from LLM ({exc}): {raw[:300]!r}") from exc


def as_str(value, default: str = "") -> str:
    """Coerce an LLM-supplied field to a string."""
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        return " ".join(as_str(v) for v in value).strip()
    return str(value).strip()


def as_str_list(value, limit: int | None = None) -> list[str]:
    """Coerce an LLM-supplied field to a list of non-empty strings."""
    if value is None:
        items = []
    elif isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = [value]

    out = [as_str(v) for v in items]
    out = [v for v in out if v]
    return out[:limit] if limit else out


_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def split_sentences(text: str) -> list[str]:
    """Split narration into sentences, preserving terminal punctuation."""
    text = (text or "").strip()
    if not text:
        return []
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks of at most max_chars, on sentence boundaries.

    A single sentence longer than max_chars is split on word boundaries rather
    than dropped or truncated — TTS providers reject oversized payloads, and
    silently losing a sentence would desync the captions from the audio.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    chunks: list[str] = []
    current = ""

    for sentence in split_sentences(text):
        pieces = [sentence]
        if len(sentence) > max_chars:
            pieces = _split_long_sentence(sentence, max_chars)

        for piece in pieces:
            if not current:
                current = piece
            elif len(current) + 1 + len(piece) <= max_chars:
                current = f"{current} {piece}"
            else:
                chunks.append(current)
                current = piece

    if current:
        chunks.append(current)
    return chunks


def _split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    """Break an over-long sentence on word boundaries."""
    pieces: list[str] = []
    current = ""
    for word in sentence.split():
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current = f"{current} {word}"
        else:
            pieces.append(current)
            current = word
    if current:
        pieces.append(current)
    return pieces


def word_count(text: str) -> int:
    """Count words in narration text."""
    return len((text or "").split())


def format_timestamp(seconds: float) -> str:
    """Format seconds as a YouTube chapter timestamp.

    Under an hour: M:SS (YouTube's own style). An hour or over: H:MM:SS.
    """
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def slugify(text: str, max_len: int = 60) -> str:
    """Filesystem-safe slug from a title."""
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:max_len] or "untitled"


def escape_concat_path(path) -> str:
    """Escape a path for an ffmpeg concat-demuxer list line.

    The demuxer reads `file '<path>'`, so an apostrophe in the path has to be
    closed, escaped, and reopened.
    """
    return str(path).replace("'", "'\\''")


def truncate_words(text: str, limit: int) -> str:
    """Trim text to at most `limit` words, on a word boundary."""
    words = (text or "").split()
    if len(words) <= limit:
        return text.strip()
    return " ".join(words[:limit]).rstrip(",;:") + "."
