"""Final render — scene clips, concat, music bed, loudness, output.

The render is deliberately two-stage. Each scene is encoded once with identical
settings so they can be concatenated with a stream copy (instant, no quality
cost), then a single final pass mixes the audio, optionally burns subtitles, and
normalises loudness.

The final pass also pads the video to the narration. Per-scene frame rounding
accumulates across a hundred clips, and a video that ends even a second before
the audio truncates the outro — so the last frame is held for the difference.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from verticals.assemble import get_audio_duration
from verticals.config import run_cmd
from verticals.log import log

from .config import FPS, MEDIA_DIR, VIDEO_HEIGHT, VIDEO_WIDTH
from .util import escape_concat_path
from .visuals import animate_scene

_filter_cache: dict[str, bool] = {}


def _has_filter(name: str) -> bool:
    """Whether this ffmpeg build ships a given filter."""
    if name in _filter_cache:
        return _filter_cache[name]
    try:
        r = run_cmd(["ffmpeg", "-hide_banner", "-filters"], capture=True)
        available = {
            line.split()[1] for line in r.stdout.splitlines() if len(line.split()) > 1
        }
        _filter_cache[name] = name in available
    except Exception:
        _filter_cache[name] = False
    return _filter_cache[name]


def _amix_supports_normalize() -> bool:
    """Whether amix accepts normalize=0 (ffmpeg 4.4+).

    Without it, amix halves both inputs and the narration lands quiet.
    """
    if "amix_normalize" in _filter_cache:
        return _filter_cache["amix_normalize"]
    try:
        r = run_cmd(["ffmpeg", "-hide_banner", "-h", "filter=amix"], capture=True)
        _filter_cache["amix_normalize"] = "normalize" in r.stdout
    except Exception:
        _filter_cache["amix_normalize"] = False
    return _filter_cache["amix_normalize"]


def render_scenes(
    scenes: list[dict],
    frames: list[Path],
    work_dir: Path,
    fade: float = 0.0,
    workers: int = 2,
    force: bool = False,
) -> list[Path]:
    """Encode every scene into a clip. Cached per scene so re-runs are cheap."""
    clips_dir = work_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    jobs = []
    for i, scene in enumerate(scenes):
        if i >= len(frames):
            break
        jobs.append((i, scene, frames[i], clips_dir / f"clip_{i:04d}.mp4"))

    def _one(job):
        i, scene, frame, out_path = job
        if out_path.exists() and not force:
            return out_path
        animate_scene(
            frame,
            out_path,
            duration=float(scene["duration"]),
            effect=scene.get("effect", "zoom_in"),
            fade=fade,
        )
        return out_path

    log(f"Rendering {len(jobs)} scene clips ({workers} at a time)...")
    clips: list[Path] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for done, path in enumerate(pool.map(_one, jobs), 1):
            clips.append(path)
            if done % 10 == 0 or done == len(jobs):
                log(f"  {done}/{len(jobs)} clips rendered")

    return clips


def concat_clips(clips: list[Path], out_path: Path) -> Path:
    """Concatenate scene clips with a stream copy.

    Safe because render_scenes encodes every clip with identical parameters.
    """
    if not clips:
        raise ValueError("No scene clips to concatenate")

    list_file = out_path.parent / f"{out_path.stem}_concat.txt"
    list_file.write_text("\n".join(f"file '{escape_concat_path(c)}'" for c in clips))

    log(f"Concatenating {len(clips)} clips...")
    run_cmd([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", str(out_path), "-y", "-loglevel", "quiet",
    ])
    return out_path


def get_video_duration(path: Path) -> float:
    """Duration of a video file in seconds."""
    r = run_cmd(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture=True,
    )
    return float(r.stdout.strip())


def finalize(
    video_path: Path,
    narration_path: Path,
    out_path: Path,
    music_path: str | None = None,
    music_volume: float = 0.16,
    duck_ratio: float = 8.0,
    ass_path: str | None = None,
    normalize_loudness: bool = True,
) -> Path:
    """Mix audio, optionally burn subtitles, and write the deliverable."""
    audio_duration = get_audio_duration(narration_path)
    video_duration = get_video_duration(video_path)
    # Hold the last frame long enough to cover the narration, plus a beat of
    # air at the end so the outro does not cut on its final syllable.
    pad = max(0.0, audio_duration - video_duration) + 0.5

    cmd = ["ffmpeg", "-i", str(video_path), "-i", str(narration_path)]

    video_chain = [f"tpad=stop_mode=clone:stop_duration={pad:.3f}"]
    if ass_path and Path(ass_path).exists():
        if _has_filter("ass"):
            escaped = (
                str(ass_path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
            )
            video_chain.append(f"ass={escaped}")
        else:
            log(
                "WARNING: this ffmpeg build has no libass — subtitles will NOT "
                "be burned in. The SRT sidecar is still uploaded to YouTube. "
                "Install an ffmpeg with libass for burn-in."
            )
    video_chain.append(f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}")

    use_music = bool(music_path and Path(music_path).exists())
    if use_music:
        cmd += ["-stream_loop", "-1", "-i", str(music_path)]

    audio_chain = _build_audio_filter(
        use_music=use_music,
        duration=audio_duration,
        music_volume=music_volume,
        duck_ratio=duck_ratio,
        normalize_loudness=normalize_loudness,
    )

    filter_complex = f"[0:v]{','.join(video_chain)}[vout]"
    if audio_chain:
        filter_complex += f";{audio_chain}"

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]" if audio_chain else "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-t", f"{audio_duration + 0.5:.3f}",
        str(out_path), "-y", "-loglevel", "error",
    ]

    log(f"Final render ({audio_duration / 60:.1f} min) — this takes a while...")
    run_cmd(cmd)
    log(f"Video rendered: {out_path}")
    return out_path


def _build_audio_filter(
    use_music: bool,
    duration: float,
    music_volume: float,
    duck_ratio: float,
    normalize_loudness: bool,
) -> str:
    """Build the audio filter graph, ending in [aout].

    With music, the bed is ducked under the narration by sidechain compression
    rather than by a scripted volume envelope. On a 15-minute track an envelope
    means hundreds of `between()` terms and it only ever approximates where the
    speech actually is; the sidechain follows the real signal.
    """
    parts = []

    if use_music:
        parts.append(
            f"[2:a]atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,"
            f"volume={music_volume}[bed]"
        )

        if _has_filter("sidechaincompress"):
            parts.append("[1:a]asplit=2[vo][key]")
            parts.append(
                "[bed][key]sidechaincompress="
                f"threshold=0.03:ratio={duck_ratio}:attack=20:release=500"
                ":makeup=1[ducked]"
            )
            voice, bed = "[vo]", "[ducked]"
        else:
            log("ffmpeg has no sidechaincompress — using a static music level")
            voice, bed = "[1:a]", "[bed]"

        normalize = ":normalize=0" if _amix_supports_normalize() else ""
        mixed = "[mixed]" if normalize_loudness else "[aout]"
        parts.append(
            f"{voice}{bed}amix=inputs=2:duration=first:dropout_transition=0"
            f"{normalize}{mixed}"
        )
        tail_in = mixed
    else:
        if not normalize_loudness:
            return ""
        tail_in = "[1:a]"

    if normalize_loudness:
        if _has_filter("loudnorm"):
            # -16 LUFS integrated: YouTube normalises to about -14, and leaving
            # a little headroom avoids the platform pulling the track down.
            parts.append(f"{tail_in}loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
        else:
            parts.append(f"{tail_in}anull[aout]")

    return ";".join(parts)


def output_path_for(project_id: str, lang: str = "en") -> Path:
    """Where the finished video lands."""
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    return MEDIA_DIR / f"longform_{project_id}_{lang}.mp4"
