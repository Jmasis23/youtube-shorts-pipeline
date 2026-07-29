"""CLI entry point — python -m longform."""

import argparse
import os
import random
import sys
from pathlib import Path

from verticals.log import log, set_verbose
from verticals.niche import list_niches

from .config import (
    MAX_TARGET_MINUTES,
    MIN_TARGET_MINUTES,
    ensure_dirs,
)
from .formats import list_formats, load_format
from .project import Project, list_projects

# Niche profile keys use the TTS library name, the CLI uses the short one.
_VOICE_PROFILE_KEYS = {"edge": "edge_tts", "edge_tts": "edge_tts"}


# ─────────────────────────────────────────────────────
# Informational commands
# ─────────────────────────────────────────────────────

def cmd_formats(args):
    names = list_formats()
    print(f"\n  Long-form formats ({len(names)}):\n")
    for name in names:
        profile = load_format(name)
        display = profile.get("display_name", name)
        minutes = profile.get("target_minutes", "?")
        chapters = profile.get("chapters", "?")
        print(f"    {name:14s}  {display}  —  ~{minutes} min, {chapters} chapters")
        desc = " ".join(profile.get("description", "").split())
        if desc:
            print(f"    {'':14s}  {desc[:100]}")
    print()


def cmd_projects(args):
    projects = list_projects(limit=args.limit)
    if not projects:
        print("\n  No projects yet. Start one with: python -m longform outline --topic '...'\n")
        return
    print(f"\n  Recent projects ({len(projects)}):\n")
    for p in projects:
        title = p["title"] or p["topic"]
        print(f"    {p['project_id']}  [{p['format']:12.12}]  {title[:60]}")
        if p["url"]:
            print(f"    {'':12s}  {p['url']}")
    print()


def cmd_status(args):
    project = Project.load(args.project)
    print()
    print(project.summary())
    print()


# ─────────────────────────────────────────────────────
# Pass one — outline
# ─────────────────────────────────────────────────────

def cmd_outline(args) -> Project:
    from .outline import generate_outline, outline_summary

    minutes = args.minutes
    if minutes is not None and not (MIN_TARGET_MINUTES <= minutes <= MAX_TARGET_MINUTES):
        print(
            f"  Error: --minutes must be between {MIN_TARGET_MINUTES} and "
            f"{MAX_TARGET_MINUTES}"
        )
        sys.exit(1)

    ensure_dirs()
    project = Project.create(args.topic, args.format, args.niche)

    outline = generate_outline(
        topic=args.topic,
        fmt=args.format,
        niche=args.niche,
        target_minutes=minutes,
        chapter_count=args.chapters,
        context=args.context,
        provider=args.provider,
        research=not args.no_research,
    )

    project.set("outline", outline)
    project.set("format", outline["format"])
    project.complete("outline")
    path = project.save()

    print(f"\n{outline_summary(outline)}\n")
    print(f"  Outline saved: {path}")
    print(f"  Next: python -m longform script --project {project.project_id}\n")
    return project


# ─────────────────────────────────────────────────────
# Pass two — script
# ─────────────────────────────────────────────────────

def cmd_script(args, project: Project | None = None) -> Project:
    from .script import script_text, write_script

    project = project or Project.load(args.project)
    outline = project.get("outline")
    if not outline:
        print("  Error: this project has no outline. Run `outline` first.")
        sys.exit(1)

    if project.is_done("script") and not getattr(args, "force", False):
        print("  Script already written (use --force to rewrite).")
        return project

    def _progress(i, total, title):
        print(f"  Writing {i}/{total}: {title}")

    sections = write_script(
        outline,
        fmt=project.get("format"),
        niche=project.get("niche"),
        provider=getattr(args, "provider", None),
        scene_seconds=getattr(args, "scene_seconds", None),
        on_progress=_progress,
    )

    total_words = sum(s["word_count"] for s in sections)
    project.set("sections", sections)
    project.set("word_count", total_words)
    project.complete("script", {"sections": len(sections), "words": total_words})
    project.save()

    script_path = project.work_dir() / "script.txt"
    script_path.write_text(script_text(sections), encoding="utf-8")

    print(f"\n  Script: {total_words} words (~{total_words / 150:.1f} min)")
    for s in sections:
        drift = s["word_count"] - s["target_words"]
        flag = "" if abs(drift) <= s["target_words"] * 0.15 else f"  ({drift:+d} off target)"
        print(f"    {s['title'][:44]:46.46} {s['word_count']:4d}w{flag}")
    print(f"\n  Full text: {script_path}")
    print(f"  Next: python -m longform produce --project {project.project_id}\n")
    return project


def cmd_import_script(args) -> Project:
    """Build a project from a script you wrote yourself.

    Sections are split on `## Heading` lines; the heading becomes the chapter
    title. Without headings the file is split on blank lines into roughly even
    sections. Visual prompts are generated per section afterwards.
    """
    from .script import write_visuals_for_imported

    path = Path(args.file)
    if not path.exists():
        print(f"  Error: no such file: {path}")
        sys.exit(1)

    raw = path.read_text(encoding="utf-8")
    sections = _split_imported(raw, args.chapters)
    if not sections:
        print("  Error: the file has no usable text.")
        sys.exit(1)

    ensure_dirs()
    project = Project.create(args.topic, args.format, args.niche)

    print(f"  Imported {len(sections)} sections from {path.name}")
    sections = write_visuals_for_imported(
        sections,
        topic=args.topic,
        fmt=args.format,
        niche=args.niche,
        provider=args.provider,
        scene_seconds=args.scene_seconds,
    )

    total_words = sum(s["word_count"] for s in sections)
    project.set(
        "outline",
        {
            "topic": args.topic,
            "format": args.format,
            "niche": args.niche,
            "working_title": args.topic,
            "thesis": "",
            "research": "",
            "chapters": [{"title": s["title"]} for s in sections if s["key"] == "chapter"],
            "keywords": [],
        },
    )
    project.set("sections", sections)
    project.set("word_count", total_words)
    project.complete("outline")
    project.complete("script", {"sections": len(sections), "words": total_words})
    project.save()

    print(f"  Project {project.project_id} ready — {total_words} words")
    print(f"  Next: python -m longform produce --project {project.project_id}\n")
    return project


def _split_imported(raw: str, max_chapters: int | None) -> list[dict]:
    """Split an imported script into sections."""
    from .util import word_count

    lines = raw.splitlines()
    has_headings = any(line.strip().startswith("##") for line in lines)

    blocks: list[tuple[str, str]] = []
    if has_headings:
        title, buf = "Intro", []
        for line in lines:
            if line.strip().startswith("##"):
                if buf and " ".join(buf).strip():
                    blocks.append((title, " ".join(buf).strip()))
                title = line.strip().lstrip("#").strip() or "Chapter"
                buf = []
            else:
                buf.append(line.strip())
        if buf and " ".join(buf).strip():
            blocks.append((title, " ".join(buf).strip()))
    else:
        paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
        count = max(1, min(max_chapters or 6, len(paragraphs)))
        per = max(1, len(paragraphs) // count)
        for i in range(0, len(paragraphs), per):
            idx = len(blocks)
            blocks.append((f"Part {idx + 1}", " ".join(paragraphs[i : i + per])))

    sections = []
    for i, (title, text) in enumerate(blocks):
        if i == 0:
            key = "intro"
        elif i == len(blocks) - 1 and len(blocks) > 2:
            key = "outro"
        else:
            key = "chapter"
        sections.append(
            {
                "key": key,
                "index": i,
                "title": title,
                "narration": text,
                "visual_prompts": [],
                "summary": "",
                "word_count": word_count(text),
                "target_words": word_count(text),
            }
        )
    return sections


# ─────────────────────────────────────────────────────
# Produce
# ─────────────────────────────────────────────────────

def cmd_produce(args, project: Project | None = None) -> Project:
    from verticals.niche import load_niche

    from .assemble import concat_clips, finalize, output_path_for, render_scenes
    from .chapters import build_markers, validate_markers
    from .formats import (
        get_audio_config,
        get_caption_config,
        get_scene_seconds,
        get_visual_config,
    )
    from .narration import synthesize_sections
    from .subtitles import generate_subtitles
    from .visuals import generate_scene_images, plan_scenes

    project = project or Project.load(args.project)
    sections = project.get("sections")
    if not sections:
        print("  Error: this project has no script. Run `script` first.")
        sys.exit(1)

    lang = args.lang
    force = args.force
    work_dir = project.work_dir(lang)

    profile = load_format(project.get("format", "explainer"))
    niche_profile = load_niche(project.get("niche", "general"))
    audio_cfg = get_audio_config(profile)
    caption_cfg = get_caption_config(profile)
    visual_cfg = get_visual_config(profile)
    scene_seconds = get_scene_seconds(profile, args.scene_seconds)

    print(f"\n  Producing project {project.project_id} [{project.get('format')}]\n")

    # ── narration ────────────────────────────────────
    tts_provider = _resolve_tts_provider(args.voice)
    voice_config = _resolve_voice_config(
        profile, niche_profile, tts_provider, lang, args.voice_id
    )

    if force or not project.is_done("narration"):
        narration = synthesize_sections(
            sections,
            work_dir,
            lang=lang,
            provider=tts_provider,
            voice_config=voice_config,
            gap_seconds=float(audio_cfg.get("chapter_gap_seconds", 0.7)),
            force=force,
        )
        project.complete(
            "narration",
            {
                "audio_path": str(narration["audio_path"]),
                "duration": narration["duration"],
                "sections": narration["sections"],
            },
        )
        project.save()
    else:
        log("Skipping narration (already done)")
        narration = {
            "audio_path": Path(project.artifact("narration", "audio_path")),
            "duration": project.artifact("narration", "duration", 0.0),
            "sections": project.artifact("narration", "sections", []),
        }

    narration_path = Path(narration["audio_path"])
    rendered_sections = narration["sections"]

    # ── chapter markers, measured from the audio ─────
    markers = build_markers(rendered_sections)
    problems = validate_markers(markers)
    project.set("chapters", markers)
    if problems:
        print("  Chapter warnings:")
        for p in problems:
            print(f"    - {p}")
        print()

    # ── scene plan ───────────────────────────────────
    if force or not project.is_done("scenes"):
        scenes = plan_scenes(
            rendered_sections,
            sections,
            scene_seconds=scene_seconds,
            motion=visual_cfg.get("motion"),
            prompt_suffix=visual_cfg.get("prompt_suffix", ""),
        )
        project.complete("scenes", {"scenes": scenes})
        project.save()
    else:
        log("Skipping scene plan (already done)")
        scenes = project.artifact("scenes", "scenes", [])

    print(
        f"  {len(scenes)} scenes over {narration['duration'] / 60:.1f} minutes "
        f"(~{scene_seconds:.0f}s each)"
    )

    # ── images ───────────────────────────────────────
    if force or not project.is_done("images"):
        frames = generate_scene_images(scenes, work_dir, workers=args.workers)
        project.complete("images", {"frames": [str(f) for f in frames]})
        project.save()
    else:
        log("Skipping image generation (already done)")
        frames = [Path(f) for f in project.artifact("images", "frames", [])]

    # ── scene clips ──────────────────────────────────
    fade = args.fade if args.fade is not None else float(visual_cfg.get("fade_seconds", 0.0))
    if force or not project.is_done("clips"):
        clips = render_scenes(
            scenes, frames, work_dir, fade=fade, workers=args.render_workers, force=force
        )
        project.complete("clips", {"clips": [str(c) for c in clips]})
        project.save()
    else:
        log("Skipping scene clips (already done)")
        clips = [Path(c) for c in project.artifact("clips", "clips", [])]

    # ── subtitles ────────────────────────────────────
    burn_in = caption_cfg.get("burn_in", False)
    if args.burn_captions:
        burn_in = True
    if args.no_captions:
        burn_in = False

    if args.no_captions:
        subtitles = {"srt_path": "", "ass_path": ""}
        log("Subtitles disabled")
    elif force or not project.is_done("subtitles"):
        subtitles = generate_subtitles(
            narration_path,
            work_dir,
            lang=lang,
            words_per_line=int(caption_cfg.get("words_per_line", 8)),
            burn_in=burn_in,
            font_family=caption_cfg.get("font_family", "Arial"),
            font_size=int(caption_cfg.get("font_size", 44)),
        )
        project.complete("subtitles", subtitles)
        project.save()
    else:
        log("Skipping subtitles (already done)")
        subtitles = {
            "srt_path": project.artifact("subtitles", "srt_path", ""),
            "ass_path": project.artifact("subtitles", "ass_path", ""),
        }

    # ── assemble ─────────────────────────────────────
    if force or not project.is_done("assemble"):
        silent_video = concat_clips(clips, work_dir / "scenes_concat.mp4")
        out_path = output_path_for(project.project_id, lang)
        finalize(
            video_path=silent_video,
            narration_path=narration_path,
            out_path=out_path,
            music_path=_resolve_music(args),
            music_volume=float(audio_cfg.get("music_volume", 0.16)),
            duck_ratio=float(audio_cfg.get("duck_ratio", 8)),
            ass_path=subtitles.get("ass_path") or None,
            normalize_loudness=not args.no_loudnorm,
        )
        project.complete("assemble", {"video_path": str(out_path)})
    else:
        log("Skipping assembly (already done)")
        out_path = Path(project.artifact("assemble", "video_path"))

    project.set("video_path", str(out_path))
    project.set("srt_path", subtitles.get("srt_path", ""))
    project.save()

    print(f"\n  Video: {out_path}")
    print(f"  Next: python -m longform upload --project {project.project_id}\n")
    return project


def _resolve_tts_provider(requested: str | None) -> str | None:
    """Pick the TTS provider for a long-form render.

    Long-form defaults to Gemini TTS (Google GenAI) when a Gemini key is
    present: it narrates far more naturally than Edge over a 15-minute runtime,
    it takes the delivery instruction the format profile supplies, and the key
    is already required for scene images. Falling back to the shared
    auto-detect chain (Edge first) when there is no key keeps the free path
    working. An explicit --voice always wins.
    """
    if requested:
        return requested

    from verticals.config import get_gemini_key

    if os.environ.get("TTS_PROVIDER"):
        return None  # let the shared resolver read the env var
    if get_gemini_key():
        return "gemini"
    return None


def _resolve_voice_config(
    fmt_profile: dict,
    niche_profile: dict,
    provider: str | None,
    lang: str,
    voice_id_override: str | None,
) -> dict:
    """Merge the format's voice settings over the niche's.

    The format owns delivery — a documentary and a countdown want different
    voices reading the same subject — so it wins where it specifies something.
    The niche fills in anything the format leaves out.
    """
    from verticals.niche import get_voice_config as niche_voice_config

    from .formats import get_voice_config as format_voice_config

    resolved = provider or "edge"
    config = niche_voice_config(
        niche_profile,
        provider=_VOICE_PROFILE_KEYS.get(resolved, resolved),
        lang=lang,
    )
    for key, value in format_voice_config(fmt_profile, provider=resolved, lang=lang).items():
        if value:
            config[key] = value

    if voice_id_override:
        config["voice_id"] = voice_id_override
    return config


def _resolve_music(args) -> str | None:
    """Pick the background track: explicit path, a random bundled one, or none."""
    if args.no_music:
        return None
    if args.music:
        path = Path(args.music)
        if not path.exists():
            log(f"Music file not found: {path} — continuing without music")
            return None
        return str(path)

    from verticals.music import _find_tracks

    tracks = _find_tracks()
    if not tracks:
        log("No tracks in music/ — continuing without background music")
        return None
    return str(random.choice(tracks))


# ─────────────────────────────────────────────────────
# Metadata + upload
# ─────────────────────────────────────────────────────

def cmd_metadata(args, project: Project | None = None) -> Project:
    from .metadata import build_description, generate_metadata

    project = project or Project.load(args.project)
    markers = project.get("chapters", [])
    if not markers:
        print("  Error: no chapter markers yet. Run `produce` first.")
        sys.exit(1)

    if project.is_done("metadata") and not getattr(args, "force", False):
        print("  Metadata already written (use --force to rewrite).")
        return project

    metadata = generate_metadata(
        project.get("outline", {}),
        markers,
        fmt=project.get("format"),
        provider=getattr(args, "provider", None),
        channel_context=getattr(args, "context", "") or "",
    )
    description = build_description(
        metadata, markers, extra_links=getattr(args, "links", "") or ""
    )

    project.data.update(metadata)
    project.set("youtube_description", description)
    project.complete("metadata")
    project.save()

    print(f"\n  Title: {metadata['youtube_title']}")
    if len(metadata.get("title_options", [])) > 1:
        print("  Alternatives:")
        for t in metadata["title_options"][1:]:
            print(f"    - {t}")
    print(f"\n  Description ({len(description)} chars):\n")
    print("\n".join(f"    {line}" for line in description.splitlines()[:20]))
    print(f"\n  Tags: {project.get('youtube_tags', '')}\n")
    return project


def cmd_upload(args, project: Project | None = None) -> str:
    from verticals.thumbnail import generate_thumbnail
    from verticals.upload import upload_to_youtube

    from .config import MEDIA_DIR

    project = project or Project.load(args.project)
    video_path = Path(project.get("video_path", ""))
    if not video_path.exists():
        print("  Error: no rendered video for this project. Run `produce` first.")
        sys.exit(1)

    if not project.is_done("metadata"):
        print("  Error: no metadata for this project. Run `metadata` first.")
        sys.exit(1)

    project.set("privacy_status", args.privacy)

    thumb_path = None
    if not args.no_thumbnail:
        if project.is_done("thumbnail") and not args.force:
            cached = project.artifact("thumbnail", "path", "")
            thumb_path = Path(cached) if cached and Path(cached).exists() else None
        else:
            try:
                thumb_path = generate_thumbnail(project.data, MEDIA_DIR)
                project.complete("thumbnail", {"path": str(thumb_path)})
                project.save()
            except Exception as e:
                log(f"Thumbnail generation failed: {e} — uploading without one")

    srt = project.get("srt_path", "")
    srt_path = Path(srt) if srt and Path(srt).exists() else None

    if project.is_done("upload") and not args.force:
        url = project.artifact("upload", "url", "")
        print(f"\n  Already uploaded: {url}\n")
        return url

    url = upload_to_youtube(
        video_path, project.data, srt_path, args.lang, thumb_path
    )
    project.complete("upload", {"url": url})
    project.set("youtube_url", url)
    project.save()

    print(f"\n  Live ({args.privacy}): {url}")
    if project.get("pinned_comment"):
        print(f"\n  Pinned comment to post:\n    {project.get('pinned_comment')}")
    print()
    return url


# ─────────────────────────────────────────────────────
# Full pipeline
# ─────────────────────────────────────────────────────

def cmd_run(args):
    project = cmd_outline(args)
    project = cmd_script(args, project)

    if args.script_only:
        print("  --script-only — stopping before render.\n")
        return

    project = cmd_produce(args, project)
    project = cmd_metadata(args, project)

    if args.no_upload:
        print("  --no-upload — stopping before upload.\n")
        return

    cmd_upload(args, project)


# ─────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────

def _add_planning_args(p):
    p.add_argument("--topic", required=True, help="What the video is about")
    p.add_argument("--format", default="explainer",
                   help=f"Format profile ({', '.join(list_formats())})")
    p.add_argument("--niche", default="general",
                   help=f"Niche profile ({', '.join(list_niches()[:8])}...)")
    p.add_argument("--minutes", type=float, default=None,
                   help="Target runtime; defaults to the format's own")
    p.add_argument("--chapters", type=int, default=None,
                   help="Body chapter count; defaults to the format's own")
    p.add_argument("--context", default="", help="Channel context for the writer")
    p.add_argument("--provider", default=None,
                   help="LLM: claude, gemini, openai, minimax, ollama, litellm")
    p.add_argument("--no-research", action="store_true",
                   help="Skip live search (claims stay general)")


def _add_produce_args(p):
    p.add_argument("--lang", default="en",
                   choices=["en", "hi", "es", "pt", "de", "fr", "ja", "ko"])
    p.add_argument("--voice", default=None,
                   help="TTS: gemini (default when GEMINI_API_KEY is set), edge, "
                        "elevenlabs, minimax, 60db, say")
    p.add_argument("--voice-id", default=None, help="Override the voice id for the provider")
    p.add_argument("--scene-seconds", type=float, default=None,
                   help="Seconds of narration per visual (default: from format)")
    p.add_argument("--workers", type=int, default=4, help="Concurrent image generations")
    p.add_argument("--render-workers", type=int, default=2,
                   help="Concurrent ffmpeg scene encodes")
    p.add_argument("--fade", type=float, default=None,
                   help="Dip-to-black seconds at each scene edge (default: from format)")
    p.add_argument("--music", default=None, help="Background track path")
    p.add_argument("--no-music", action="store_true", help="No background music")
    p.add_argument("--burn-captions", action="store_true", help="Force burned-in subtitles")
    p.add_argument("--no-captions", action="store_true", help="Skip subtitles entirely")
    p.add_argument("--no-loudnorm", action="store_true", help="Skip loudness normalisation")
    p.add_argument("--force", action="store_true", help="Redo stages already marked done")


def _add_upload_args(p):
    p.add_argument("--lang", default="en",
                   choices=["en", "hi", "es", "pt", "de", "fr", "ja", "ko"])
    p.add_argument("--privacy", default="private",
                   choices=["private", "unlisted", "public"])
    p.add_argument("--no-thumbnail", action="store_true", help="Upload without a thumbnail")
    p.add_argument("--force", action="store_true", help="Re-upload even if already done")


def main():
    parser = argparse.ArgumentParser(
        prog="longform",
        description="Longform — faceless long-form YouTube video engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Typical run:\n"
            "  python -m longform run --topic 'How container shipping actually works' \\\n"
            "      --format documentary --niche general --minutes 14\n"
        ),
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("formats", help="List long-form format profiles")

    p_projects = sub.add_parser("projects", help="List recent projects")
    p_projects.add_argument("--limit", type=int, default=20)

    p_status = sub.add_parser("status", help="Show a project's stage status")
    p_status.add_argument("--project", required=True, help="Project id or path")

    p_outline = sub.add_parser("outline", help="Pass one: plan the chapters")
    _add_planning_args(p_outline)

    p_script = sub.add_parser("script", help="Pass two: write the narration")
    p_script.add_argument("--project", required=True)
    p_script.add_argument("--provider", default=None)
    p_script.add_argument("--scene-seconds", type=float, default=None)
    p_script.add_argument("--force", action="store_true")

    p_import = sub.add_parser("import-script", help="Start from a script you wrote")
    p_import.add_argument("--file", required=True, help="Script file (## headings split chapters)")
    p_import.add_argument("--topic", required=True)
    p_import.add_argument("--format", default="explainer")
    p_import.add_argument("--niche", default="general")
    p_import.add_argument("--chapters", type=int, default=6,
                          help="Sections to split into when the file has no headings")
    p_import.add_argument("--provider", default=None)
    p_import.add_argument("--scene-seconds", type=float, default=None)

    p_produce = sub.add_parser("produce", help="Narrate, generate scenes, render")
    p_produce.add_argument("--project", required=True)
    _add_produce_args(p_produce)

    p_meta = sub.add_parser("metadata", help="Write title, description, chapters, tags")
    p_meta.add_argument("--project", required=True)
    p_meta.add_argument("--provider", default=None)
    p_meta.add_argument("--context", default="")
    p_meta.add_argument("--links", default="", help="Extra links appended to the description")
    p_meta.add_argument("--force", action="store_true")

    p_upload = sub.add_parser("upload", help="Upload to YouTube")
    p_upload.add_argument("--project", required=True)
    _add_upload_args(p_upload)

    p_run = sub.add_parser("run", help="Full pipeline: outline -> script -> produce -> upload")
    _add_planning_args(p_run)
    _add_produce_args(p_run)
    p_run.add_argument("--privacy", default="private",
                       choices=["private", "unlisted", "public"])
    p_run.add_argument("--no-thumbnail", action="store_true")
    p_run.add_argument("--links", default="")
    p_run.add_argument("--script-only", action="store_true",
                       help="Stop after writing the script")
    p_run.add_argument("--no-upload", action="store_true",
                       help="Render and write metadata, but do not upload")

    args = parser.parse_args()

    if args.verbose:
        set_verbose(True)

    if not args.cmd:
        parser.print_help()
        return

    handlers = {
        "formats": cmd_formats,
        "projects": cmd_projects,
        "status": cmd_status,
        "outline": cmd_outline,
        "script": cmd_script,
        "import-script": cmd_import_script,
        "produce": cmd_produce,
        "metadata": cmd_metadata,
        "upload": cmd_upload,
        "run": cmd_run,
    }
    handlers[args.cmd](args)


if __name__ == "__main__":
    main()
