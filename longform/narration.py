"""Narration synthesis — chunked TTS per section, concatenated with real timings.

A 15-minute script is far past what any TTS provider will accept in one
request, so narration is synthesized per section and, within a section, in
sentence-aligned chunks. Sections are rendered as separate audio files on
purpose: measuring each one gives the exact chapter start times, which is what
the YouTube chapter markers and the scene plan are both built from.

Work is cached per section, so a provider failure ten minutes into a render
resumes rather than re-synthesizing everything.
"""

from pathlib import Path

from verticals.assemble import get_audio_duration
from verticals.config import run_cmd
from verticals.log import log
from verticals.tts import generate_voiceover

from .config import DEFAULT_CHAPTER_GAP, TTS_CHUNK_CHARS
from .util import chunk_text, escape_concat_path


def synthesize_sections(
    sections: list[dict],
    work_dir: Path,
    lang: str = "en",
    provider: str | None = None,
    voice_config: dict | None = None,
    gap_seconds: float = DEFAULT_CHAPTER_GAP,
    force: bool = False,
) -> dict:
    """Synthesize narration for every section and stitch it into one track.

    Returns:
        {
          "audio_path": Path,          # the full narration
          "duration": float,           # total seconds including gaps
          "sections": [                # in order, with measured timings
             {"index", "key", "title", "path", "duration", "start", "end"}
          ],
        }
    """
    audio_dir = work_dir / "narration"
    audio_dir.mkdir(parents=True, exist_ok=True)

    rendered = []
    for i, section in enumerate(sections):
        out_path = audio_dir / f"section_{i:02d}.mp3"

        if out_path.exists() and not force:
            log(f"Narration {i + 1}/{len(sections)} cached: {section['title']}")
        else:
            log(f"Narrating {i + 1}/{len(sections)}: {section['title']}")
            _synthesize_one(
                text=section["narration"],
                out_path=out_path,
                work_dir=audio_dir / f"chunks_{i:02d}",
                lang=lang,
                provider=provider,
                voice_config=voice_config,
            )

        rendered.append(
            {
                "index": i,
                "key": section.get("key", "chapter"),
                "title": section.get("title", f"Section {i}"),
                "path": str(out_path),
                "duration": get_audio_duration(out_path),
            }
        )

    gap_path = None
    if gap_seconds > 0 and len(rendered) > 1:
        gap_path = _silence(audio_dir, gap_seconds)

    full_path = work_dir / "narration_full.mp3"
    _concat_audio(
        [Path(r["path"]) for r in rendered],
        full_path,
        gap_path=gap_path,
    )

    # Lay the measured durations onto a timeline. Each gap sits *after* its
    # section, so section N starts after N sections and N gaps.
    effective_gap = gap_seconds if gap_path else 0.0
    cursor = 0.0
    for i, r in enumerate(rendered):
        # The last section has no gap after it.
        r["gap_after"] = effective_gap if i < len(rendered) - 1 else 0.0
        r["start"] = cursor
        r["end"] = cursor + r["duration"]
        cursor = r["end"] + r["gap_after"]

    total = get_audio_duration(full_path)
    log(
        f"Narration assembled: {len(rendered)} sections, "
        f"{total / 60:.1f} min total"
    )

    return {"audio_path": full_path, "duration": total, "sections": rendered}


def _synthesize_one(
    text: str,
    out_path: Path,
    work_dir: Path,
    lang: str,
    provider: str | None,
    voice_config: dict | None,
):
    """Synthesize one section, chunking if it exceeds the provider-safe size."""
    work_dir.mkdir(parents=True, exist_ok=True)
    chunks = chunk_text(text, TTS_CHUNK_CHARS)

    if not chunks:
        raise ValueError(f"Nothing to narrate for {out_path.name}")

    if len(chunks) == 1:
        produced = generate_voiceover(
            chunks[0], work_dir, lang, provider=provider, voice_config=voice_config
        )
        _copy_audio(Path(produced), out_path)
        return

    log(f"  Section split into {len(chunks)} TTS chunks")
    chunk_paths = []
    for i, chunk in enumerate(chunks):
        chunk_dir = work_dir / f"c{i:03d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        produced = generate_voiceover(
            chunk, chunk_dir, lang, provider=provider, voice_config=voice_config
        )
        chunk_paths.append(Path(produced))

    _concat_audio(chunk_paths, out_path)


def _copy_audio(src: Path, dst: Path):
    """Normalise a provider's output to mp3 at the expected path."""
    if src.resolve() == dst.resolve():
        return
    if src.suffix.lower() == ".mp3":
        dst.write_bytes(src.read_bytes())
        return
    run_cmd([
        "ffmpeg", "-i", str(src), "-c:a", "libmp3lame", "-q:a", "2",
        str(dst), "-y", "-loglevel", "quiet",
    ])


def _silence(out_dir: Path, seconds: float) -> Path:
    """Render a silent mp3 used as the gap between sections."""
    path = out_dir / f"silence_{seconds:.2f}.mp3"
    if path.exists():
        return path
    run_cmd([
        "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-t", f"{seconds:.3f}", "-c:a", "libmp3lame", "-q:a", "2",
        str(path), "-y", "-loglevel", "quiet",
    ])
    return path


def _concat_audio(parts: list[Path], out_path: Path, gap_path: Path | None = None):
    """Concatenate audio files, optionally interleaving a gap between them.

    Re-encodes rather than stream-copying: the parts can come from different
    providers (or from a mid-run provider fallback) with different sample rates,
    and a copy-concat of mismatched streams produces audio that drifts out of
    sync with the captions.
    """
    if not parts:
        raise ValueError("No audio parts to concatenate")

    sequence: list[Path] = []
    for i, part in enumerate(parts):
        if i and gap_path:
            sequence.append(gap_path)
        sequence.append(part)

    list_file = out_path.parent / f"{out_path.stem}_concat.txt"
    list_file.write_text("\n".join(f"file '{escape_concat_path(p)}'" for p in sequence))

    run_cmd([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c:a", "libmp3lame", "-q:a", "2", "-ar", "44100", "-ac", "1",
        str(out_path), "-y", "-loglevel", "quiet",
    ])
