"""Long-form paths, video constants, and pacing math.

API keys, the `~/.verticals` home, and `run_cmd` are reused from
`verticals.config` so both engines share one credential store.
"""

from pathlib import Path

from verticals.config import SKILL_DIR

# ─────────────────────────────────────────────────────
# Paths — long-form artifacts live beside the shorts ones
# ─────────────────────────────────────────────────────
LONGFORM_DIR = SKILL_DIR / "longform"
PROJECTS_DIR = LONGFORM_DIR / "projects"
MEDIA_DIR = LONGFORM_DIR / "media"
CACHE_DIR = LONGFORM_DIR / "cache"

# ─────────────────────────────────────────────────────
# Video constants — 16:9 landscape, the long-form format
# ─────────────────────────────────────────────────────
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

# ─────────────────────────────────────────────────────
# Pacing
# ─────────────────────────────────────────────────────
# Measured narration pace for TTS voices at default speed. Used to convert a
# target runtime into a word budget before anything is synthesized; the real
# runtime is measured from the rendered audio afterwards.
WORDS_PER_MINUTE = 150

# One new visual every ~9s: slow enough to read, fast enough to not feel like
# a slideshow. Overridable per format profile and per run.
DEFAULT_SCENE_SECONDS = 9.0
MIN_SCENE_SECONDS = 3.0
MAX_SCENE_SECONDS = 20.0

# Silence inserted between chapters so chapter transitions breathe.
DEFAULT_CHAPTER_GAP = 0.7

# TTS providers degrade or reject very long inputs (ElevenLabs caps at ~5k
# chars, Edge TTS gets flaky past a few thousand). Narration is synthesized in
# chunks this size, split on sentence boundaries, then concatenated.
TTS_CHUNK_CHARS = 1200

# Runtime bounds. Below 3 minutes YouTube treats it as short-form-ish content
# and the chapter machinery is pointless; above 60 the render time and image
# spend stop being reasonable for a single pass.
MIN_TARGET_MINUTES = 3
MAX_TARGET_MINUTES = 60

# YouTube's own rules for chapters to activate on a video.
YOUTUBE_MIN_CHAPTERS = 3
YOUTUBE_MIN_CHAPTER_SECONDS = 10


def words_for_minutes(minutes: float, wpm: int = WORDS_PER_MINUTE) -> int:
    """Word budget for a target runtime in minutes."""
    return int(minutes * wpm)


def minutes_for_words(words: int, wpm: int = WORDS_PER_MINUTE) -> float:
    """Estimated runtime in minutes for a word count."""
    return words / float(wpm)


def chapter_word_budgets(
    target_minutes: float,
    chapter_count: int,
    intro_share: float = 0.08,
    outro_share: float = 0.06,
) -> dict:
    """Split a runtime budget into intro / per-chapter / outro word counts.

    The intro and outro are deliberately short: on long-form, the first 30
    seconds decide retention and a long outro is where viewers leave. The
    remaining budget is divided evenly across the body chapters.

    Returns {"intro": int, "chapters": [int, ...], "outro": int, "total": int}.
    """
    chapter_count = max(1, int(chapter_count))
    total = words_for_minutes(target_minutes)

    intro = int(total * intro_share)
    outro = int(total * outro_share)
    body = max(total - intro - outro, chapter_count * 50)

    per = body // chapter_count
    budgets = [per] * chapter_count
    # Give the remainder to the first chapter — the one doing the most work.
    budgets[0] += body - per * chapter_count

    return {
        "intro": intro,
        "chapters": budgets,
        "outro": outro,
        "total": intro + sum(budgets) + outro,
    }


def scene_count_for(duration_seconds: float, scene_seconds: float) -> int:
    """How many distinct visuals to show across a span of narration."""
    scene_seconds = max(MIN_SCENE_SECONDS, min(MAX_SCENE_SECONDS, scene_seconds))
    return max(1, round(duration_seconds / scene_seconds))


def ensure_dirs():
    """Create the long-form working directories."""
    for d in (LONGFORM_DIR, PROJECTS_DIR, MEDIA_DIR, CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)
