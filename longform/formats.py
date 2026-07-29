"""Format profile loader — the long-form counterpart to niche profiles.

A *niche* (verticals/niches/*.yaml) says what the video is about: tone, visual
vocabulary, music mood. A *format* (formats/*.yaml) says how a 10-20 minute
video is built: how many chapters, what each one has to accomplish, where the
open loops go, how often to re-hook, how the payoff lands.

The two compose — `--format documentary --niche tech` writes a documentary
about tech. The format owns structure, the niche owns flavour.
"""

from pathlib import Path

import yaml

from verticals.log import log

FORMATS_DIR = Path(__file__).resolve().parent.parent / "formats"

_cache: dict[str, dict] = {}


def load_format(name: str = "explainer") -> dict:
    """Load a format profile by name, falling back to `explainer`."""
    name = (name or "explainer").strip().lower()

    if name in _cache:
        return _cache[name]

    path = FORMATS_DIR / f"{name}.yaml"
    if not path.exists():
        log(f"Format profile '{name}' not found at {path}")
        if name != "explainer":
            log("Falling back to 'explainer' format")
            return load_format("explainer")
        return _minimal_format(name)

    try:
        with open(path, "r", encoding="utf-8") as f:
            profile = yaml.safe_load(f) or {}
        profile.setdefault("name", name)
        _cache[name] = profile
        log(f"Loaded format profile: {name}")
        return profile
    except Exception as e:
        log(f"Failed to parse format profile '{name}': {e}")
        return _minimal_format(name)


def _minimal_format(name: str) -> dict:
    """Bare-minimum profile when the YAML is missing or broken."""
    return {
        "name": name,
        "display_name": name.title(),
        "target_minutes": 10,
        "chapters": 5,
        "script": {
            "tone": "clear, authoritative, conversational",
            "narration_style": "second person, plain language, no filler",
        },
        "visuals": {"scene_seconds": 9},
        "audio": {},
        "captions": {},
        "thumbnail": {},
        "metadata": {},
    }


def list_formats() -> list[str]:
    """List available format profile names."""
    if not FORMATS_DIR.exists():
        return ["explainer"]
    names = [p.stem for p in FORMATS_DIR.glob("*.yaml")]
    if "explainer" not in names:
        names.append("explainer")
    return sorted(names)


# ─────────────────────────────────────────────────────
# Stage-specific views onto the profile
# ─────────────────────────────────────────────────────

def get_target_minutes(profile: dict, override: float | None = None) -> float:
    """Runtime target: CLI override wins, then the profile, then 10 minutes."""
    if override:
        return float(override)
    return float(profile.get("target_minutes", 10))


def get_chapter_count(profile: dict, override: int | None = None) -> int:
    """Body chapter count: CLI override wins, then the profile, then 5."""
    if override:
        return int(override)
    return int(profile.get("chapters", 5))


def get_scene_seconds(profile: dict, override: float | None = None) -> float:
    """Seconds of narration per distinct visual."""
    if override:
        return float(override)
    return float(profile.get("visuals", {}).get("scene_seconds", 9))


def get_structure_context(profile: dict) -> str:
    """Build the structural-intelligence block for the outline prompt."""
    script = profile.get("script", {})
    parts = [f"FORMAT: {profile.get('display_name', profile.get('name', 'Explainer'))}"]

    if profile.get("description"):
        parts.append(f"FORMAT INTENT: {profile['description']}")
    if script.get("tone"):
        parts.append(f"TONE: {script['tone']}")
    if script.get("narration_style"):
        parts.append(f"NARRATION STYLE: {script['narration_style']}")
    if script.get("perspective"):
        parts.append(f"PERSPECTIVE: {script['perspective']}")

    arc = script.get("arc", {})
    if arc:
        parts.append("CHAPTER ARC (each chapter must do its job):")
        for key in ("intro", "early", "middle", "late", "outro"):
            if arc.get(key):
                parts.append(f"  {key}: {arc[key]}")

    retention = script.get("retention", {})
    if retention:
        parts.append("RETENTION MECHANICS:")
        if retention.get("open_loop"):
            parts.append(f"  Open loop: {retention['open_loop']}")
        if retention.get("rehook_every_seconds"):
            parts.append(
                f"  Re-hook the viewer roughly every "
                f"{retention['rehook_every_seconds']}s of narration"
            )
        for rule in retention.get("rules", []):
            parts.append(f"  - {rule}")

    hooks = script.get("hooks", [])
    if hooks:
        parts.append("COLD-OPEN HOOK PATTERNS (pick the best fit for this topic):")
        for h in hooks:
            template = h.get("template") if isinstance(h, dict) else str(h)
            if not template:
                continue
            when = h.get("when", "") if isinstance(h, dict) else ""
            line = f"  \"{template}\""
            if when:
                line += f" (use when: {when})"
            parts.append(line)

    if script.get("cta"):
        parts.append(f"CALL TO ACTION: {script['cta']}")

    forbidden = script.get("forbidden_phrases", [])
    if forbidden:
        parts.append(f"NEVER USE THESE PHRASES: {', '.join(forbidden)}")

    return "\n".join(parts)


def get_voice_config(profile: dict, provider: str = "gemini", lang: str = "en") -> dict:
    """Narration voice settings for a provider, from the format profile.

    Returns {voice_id, style_prompt, ...}. `style_prompt` only reaches providers
    that accept a delivery instruction — Gemini TTS does, and it is what lets a
    format shape how the narration is *read* rather than only how it is written.
    Anything absent here falls back to the niche profile's voice.
    """
    voice = profile.get("voice", {}) or {}
    config = {"style_prompt": voice.get("style_prompt", "")}

    suggested = (voice.get("suggested_voices", {}) or {}).get(provider)
    if isinstance(suggested, dict):
        config["voice_id"] = (
            suggested.get(lang) or suggested.get("en") or suggested.get("voice_id", "")
        )
        if suggested.get("settings"):
            config["settings"] = suggested["settings"]
        if suggested.get("model"):
            config["model"] = suggested["model"]
    elif isinstance(suggested, str):
        config["voice_id"] = suggested

    return config


def get_audio_config(profile: dict) -> dict:
    """Music and pacing settings for the audio stage."""
    defaults = {
        "music_mood": "ambient, cinematic, no lyrics",
        "music_volume": 0.18,
        "duck_ratio": 8,
        "chapter_gap_seconds": 0.7,
    }
    defaults.update(profile.get("audio", {}))
    return defaults


def get_caption_config(profile: dict) -> dict:
    """Subtitle settings.

    Long-form defaults to burn_in: false — an SRT sidecar drives YouTube's own
    CC track, which viewers can turn off. Burned-in word-popping captions are a
    short-form convention and read as noise on a 15-minute video.
    """
    defaults = {
        "burn_in": False,
        "font_family": "Arial",
        "font_size": 44,
        "words_per_line": 8,
        "text_color": "#FFFFFF",
    }
    defaults.update(profile.get("captions", {}))
    return defaults


def get_visual_config(profile: dict) -> dict:
    """Visual style settings for scene prompt generation."""
    defaults = {
        "style": "cinematic, photorealistic, shallow depth of field",
        "mood": "considered, atmospheric",
        "scene_seconds": 9,
        "prompt_suffix": "cinematic lighting, 16:9 composition, high detail, no text",
        "motion": ["zoom_in", "pan_right", "zoom_out", "pan_left"],
        # Seconds of dip-to-black at each end of a scene. 0 means hard cuts.
        "fade_seconds": 0.0,
        "subjects": {"prefer": [], "avoid": []},
    }
    defaults.update(profile.get("visuals", {}))
    return defaults


def get_metadata_config(profile: dict) -> dict:
    """YouTube metadata defaults for this format."""
    defaults = {
        # 27 = Education. Long-form faceless channels are overwhelmingly
        # Education / People & Blogs / Entertainment; Education is the safest
        # default and is overridable per format and per run.
        "category_id": "27",
        "title_style": "specific, curiosity-driven, no clickbait punctuation",
    }
    defaults.update(profile.get("metadata", {}))
    return defaults


def get_thumbnail_config(profile: dict) -> dict:
    """Thumbnail guidance for this format."""
    return profile.get("thumbnail", {})
