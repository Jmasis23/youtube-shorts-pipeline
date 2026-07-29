"""YouTube metadata — titles, description with chapters, tags, pinned comment.

Long-form metadata does more work than short-form metadata. The title and
thumbnail carry browse and suggested traffic, the description carries search,
and the chapter block carries navigation and key-moments eligibility. So the
description is assembled from the *measured* chapter markers rather than being
generated as free text, and the LLM only writes the parts it should own.
"""

from verticals.llm import call_llm
from verticals.log import log

from .chapters import chapters_block
from .formats import get_metadata_config, load_format
from .util import as_str, as_str_list, parse_json_response

YOUTUBE_TITLE_LIMIT = 100
YOUTUBE_DESCRIPTION_LIMIT = 5000
# YouTube's hard cap is 500 characters across all tags.
YOUTUBE_TAGS_CHAR_LIMIT = 480


def generate_metadata(
    outline: dict,
    markers: list[dict],
    fmt: str | None = None,
    provider: str | None = None,
    channel_context: str = "",
) -> dict:
    """Write the title options, description body, tags, and pinned comment."""
    profile = load_format(fmt or outline.get("format", "explainer"))
    meta_config = get_metadata_config(profile)

    chapter_titles = "\n".join(
        f"  {m['timestamp']} {m['title']}" for m in markers
    )
    runtime_min = max((m["end"] for m in markers), default=0) / 60
    channel_note = f"\nCHANNEL CONTEXT: {channel_context}" if channel_context else ""

    prompt = f"""Write the YouTube metadata for a finished {runtime_min:.0f}-minute \
faceless long-form video.{channel_note}

TOPIC: {outline.get('topic', '')}
THESIS: {outline.get('thesis', '')}
PROMISE TO THE VIEWER: {outline.get('audience_promise', '')}
THE VIDEO BUILDS TO: {outline.get('payoff', '')}
WORKING TITLE: {outline.get('working_title', '')}

ACTUAL CHAPTERS (measured from the rendered audio — do not invent others):
{chapter_titles}

TITLE STYLE FOR THIS FORMAT: {meta_config.get('title_style', '')}

Requirements:
- Three title options, best first, each under {YOUTUBE_TITLE_LIMIT} characters. \
The first 40 characters have to work on their own — that is all a phone shows.
- The description opens with two or three sentences that restate the promise \
for someone deciding whether to watch. Search reads this; write it for a human \
who is still hovering over the thumbnail.
- Then a longer body: what the video covers, why it is worth 15 minutes, and \
the specific questions it answers. Several short paragraphs.
- Do NOT include the chapter timestamps — they are inserted automatically.
- Tags: 12 to 18, lowercase, a mix of broad and specific, no hashtag symbols.
- A pinned comment that asks one genuine question the video leaves open. Not \
an engagement prompt, not "what did you think".
- No emoji, no ALL CAPS, no "link in bio", no fake urgency.

Output JSON exactly, with no prose around it:
{{
  "titles": ["best", "second", "third"],
  "description_intro": "the opening two or three sentences",
  "description_body": "the longer body, plain text with blank lines between paragraphs",
  "tags": ["...", "..."],
  "pinned_comment": "...",
  "thumbnail_prompt": "16:9 thumbnail image description, no text in the image"
}}"""

    log("Writing YouTube metadata...")
    data = parse_json_response(call_llm(prompt, provider=provider, max_tokens=2500))

    titles = as_str_list(data.get("titles"), limit=3) or [
        outline.get("working_title", "Untitled")
    ]
    titles = [t[:YOUTUBE_TITLE_LIMIT] for t in titles]

    tags = _fit_tags(
        as_str_list(data.get("tags"), limit=20) or outline.get("keywords", [])
    )

    return {
        "youtube_title": titles[0],
        "title_options": titles,
        "description_intro": as_str(data.get("description_intro")),
        "description_body": as_str(data.get("description_body")),
        "youtube_tags": ",".join(tags),
        "pinned_comment": as_str(data.get("pinned_comment")),
        "thumbnail_prompt": as_str(data.get("thumbnail_prompt"))
        or outline.get("thumbnail_prompt", ""),
        "youtube_category_id": meta_config.get("category_id", "27"),
    }


def build_description(
    metadata: dict,
    markers: list[dict],
    extra_links: str = "",
) -> str:
    """Assemble the final description around the measured chapter block.

    Order matters: the intro paragraph sits above the fold where search and the
    "...more" preview read it, chapters come next so they are reachable in one
    tap, and everything else follows.
    """
    sections = []

    intro = metadata.get("description_intro", "").strip()
    if intro:
        sections.append(intro)

    if markers:
        sections.append("Chapters:\n" + chapters_block(markers))

    body = metadata.get("description_body", "").strip()
    if body:
        sections.append(body)

    if extra_links.strip():
        sections.append(extra_links.strip())

    description = "\n\n".join(sections)
    if len(description) > YOUTUBE_DESCRIPTION_LIMIT:
        description = description[: YOUTUBE_DESCRIPTION_LIMIT - 3].rstrip() + "..."
    return description


def _fit_tags(tags: list[str]) -> list[str]:
    """Trim tags to YouTube's 500-character total budget."""
    kept: list[str] = []
    used = 0
    for tag in tags:
        tag = tag.strip().lstrip("#").lower()
        if not tag or tag in kept:
            continue
        cost = len(tag) + 1
        if used + cost > YOUTUBE_TAGS_CHAR_LIMIT:
            break
        kept.append(tag)
        used += cost
    return kept
