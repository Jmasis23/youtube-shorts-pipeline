"""YouTube chapter markers, measured from the rendered narration.

Chapters are the single highest-leverage long-form feature: they put a
navigable table of contents under the player, they surface in search as key
moments, and they measurably improve session time on videos over ten minutes.

They are also easy to get wrong. YouTube only activates chapters when the first
timestamp is 0:00, there are at least three of them, and every one runs at
least ten seconds. These are built from the measured duration of each rendered
section — never from an estimate — and validated against those rules before the
description is written.
"""

from .config import YOUTUBE_MIN_CHAPTERS, YOUTUBE_MIN_CHAPTER_SECONDS
from .util import format_timestamp


def build_markers(rendered_sections: list[dict]) -> list[dict]:
    """Turn measured section timings into chapter markers.

    The intro is forced to 0:00 regardless of what it measured at, because
    YouTube rejects the whole chapter list otherwise.
    """
    markers = []
    for i, section in enumerate(rendered_sections):
        start = 0.0 if i == 0 else float(section.get("start", 0.0))
        markers.append(
            {
                "index": i,
                "start": start,
                "end": float(section.get("end", start)),
                "duration": float(section.get("duration", 0.0)),
                "title": section.get("title", f"Part {i}"),
                "timestamp": format_timestamp(start),
            }
        )
    return markers


def validate_markers(markers: list[dict]) -> list[str]:
    """Check markers against YouTube's chapter rules.

    Returns a list of human-readable problems; empty means chapters will
    activate. Short sections are reported rather than silently merged — merging
    would desync the chapter titles from the narration they label.
    """
    problems = []

    if len(markers) < YOUTUBE_MIN_CHAPTERS:
        problems.append(
            f"only {len(markers)} chapters — YouTube needs at least "
            f"{YOUTUBE_MIN_CHAPTERS} for chapters to activate"
        )

    if markers and markers[0]["start"] != 0.0:
        problems.append("the first chapter must start at 0:00")

    for m in markers:
        if m["duration"] < YOUTUBE_MIN_CHAPTER_SECONDS:
            problems.append(
                f"chapter '{m['title']}' runs {m['duration']:.0f}s — "
                f"under YouTube's {YOUTUBE_MIN_CHAPTER_SECONDS}s minimum"
            )

    starts = [m["start"] for m in markers]
    if starts != sorted(starts):
        problems.append("chapter timestamps are not in ascending order")

    return problems


def chapters_block(markers: list[dict]) -> str:
    """Render the timestamp block that goes at the top of the description."""
    return "\n".join(f"{m['timestamp']} {m['title']}" for m in markers)


def total_runtime(markers: list[dict]) -> float:
    """Total runtime implied by the markers."""
    return max((m["end"] for m in markers), default=0.0)
