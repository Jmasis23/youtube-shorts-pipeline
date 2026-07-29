"""Scene planning and 16:9 b-roll generation.

A 15-minute video needs roughly a hundred distinct visuals. Three things follow
from that number, and they are what this module exists to handle:

1. Scenes are planned against *measured* section durations, so the visuals stay
   locked to the narration even when a section runs long.
2. Images are generated concurrently and cached by prompt hash, so a re-render
   costs nothing and a partial failure does not restart the batch.
3. A failed image degrades to a generated gradient rather than aborting the
   run — one dead frame in a hundred is not worth losing the render.
"""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from verticals.broll import _generate_image_gemini
from verticals.config import get_gemini_key, run_cmd
from verticals.log import log

from .config import CACHE_DIR, FPS, VIDEO_HEIGHT, VIDEO_WIDTH, scene_count_for
from .formats import get_visual_config

DEFAULT_MOTION = ["zoom_in", "pan_right", "zoom_out", "pan_left"]


def plan_scenes(
    rendered_sections: list[dict],
    sections: list[dict],
    scene_seconds: float,
    motion: list[str] | None = None,
    prompt_suffix: str = "",
) -> list[dict]:
    """Build the scene list from measured audio durations.

    Each section gets as many scenes as its runtime supports, drawing on the
    visual prompts written alongside its narration. When a section runs longer
    than its prompts cover, prompts are reused in order with a different camera
    move each time, so a repeated image never repeats identically.

    Returns an ordered list of
        {"index", "section_index", "prompt", "duration", "start", "effect"}.
    """
    motion = motion or DEFAULT_MOTION
    scenes: list[dict] = []
    cursor = 0.0

    for rendered in rendered_sections:
        idx = rendered["index"]
        section = sections[idx] if idx < len(sections) else {}
        prompts = section.get("visual_prompts") or []
        duration = float(rendered["duration"])

        count = scene_count_for(duration, scene_seconds)
        per_scene = duration / count if count else duration

        for i in range(count):
            base = prompts[i % len(prompts)] if prompts else _fallback_prompt(section)
            scenes.append(
                {
                    "index": len(scenes),
                    "section_index": idx,
                    "section_title": rendered.get("title", ""),
                    "prompt": _compose_prompt(base, prompt_suffix),
                    "duration": round(per_scene, 3),
                    "start": round(cursor, 3),
                    "effect": motion[len(scenes) % len(motion)],
                }
            )
            cursor += per_scene

        # Absorb the inter-section gap into the last scene of the section so the
        # visuals stay flush with the audio timeline rather than drifting early.
        gap = float(rendered.get("gap_after", 0.0))
        if gap and scenes:
            scenes[-1]["duration"] = round(scenes[-1]["duration"] + gap, 3)
            cursor += gap

    log(f"Planned {len(scenes)} scenes across {len(rendered_sections)} sections")
    return scenes


def _compose_prompt(base: str, suffix: str) -> str:
    """Append the format's style suffix to a scene prompt."""
    base = (base or "").strip().rstrip(".")
    suffix = " ".join((suffix or "").split())
    return f"{base}. {suffix}" if suffix else base


def _fallback_prompt(section: dict) -> str:
    """Used when a section arrived with no visual prompts at all."""
    title = section.get("title", "the subject")
    return f"Atmospheric establishing shot evoking {title}, no people, natural light"


# ─────────────────────────────────────────────────────
# Image generation
# ─────────────────────────────────────────────────────

def generate_scene_images(
    scenes: list[dict],
    work_dir: Path,
    workers: int = 4,
    use_cache: bool = True,
) -> list[Path]:
    """Generate one 16:9 image per scene, concurrently, with caching.

    Returns image paths in scene order. Without a Gemini key, every scene gets a
    generated gradient — the pipeline stays runnable end to end so timings,
    chapters, and audio can be checked before paying for images.
    """
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    api_key = get_gemini_key()
    if not api_key:
        log(
            "GEMINI_API_KEY not set — rendering gradient placeholder scenes. "
            "Get an AI Studio key at https://aistudio.google.com/apikey "
            "(Vertex AI / service-account credentials are rejected with a 403)."
        )
        return [
            _gradient_frame(i, frames_dir) for i in range(len(scenes))
        ]

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    results: list[Path | None] = [None] * len(scenes)

    def _one(i: int) -> tuple[int, Path]:
        scene = scenes[i]
        out_path = frames_dir / f"scene_{i:04d}.png"

        if out_path.exists():
            return i, out_path

        cached = _cache_path(scene["prompt"]) if use_cache else None
        if cached and cached.exists():
            out_path.write_bytes(cached.read_bytes())
            return i, out_path

        try:
            _generate_image_gemini(scene["prompt"], out_path, api_key)
            _fit_landscape(out_path)
            if cached:
                cached.write_bytes(out_path.read_bytes())
        except Exception as e:
            log(f"Scene {i + 1}/{len(scenes)} image failed: {e} — using gradient")
            return i, _gradient_frame(i, frames_dir)

        return i, out_path

    log(f"Generating {len(scenes)} scene images ({workers} at a time)...")
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for done, (i, path) in enumerate(pool.map(_one, range(len(scenes))), 1):
            results[i] = path
            if done % 10 == 0 or done == len(scenes):
                log(f"  {done}/{len(scenes)} scene images ready")

    return [p for p in results if p is not None]


def _cache_path(prompt: str) -> Path:
    """Content-addressed cache path for a prompt."""
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:32]
    return CACHE_DIR / f"{digest}.png"


def _fit_landscape(path: Path):
    """Centre-crop and resize a generated image to exactly 16:9."""
    img = Image.open(path).convert("RGB")
    orig_w, orig_h = img.size
    scale = max(VIDEO_WIDTH / orig_w, VIDEO_HEIGHT / orig_h)
    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - VIDEO_WIDTH) // 2
    top = (new_h - VIDEO_HEIGHT) // 2
    img.crop((left, top, left + VIDEO_WIDTH, top + VIDEO_HEIGHT)).save(path)


# A muted palette that reads as intentional rather than as an error frame.
_GRADIENT_PALETTE = [
    ((18, 24, 38), (48, 38, 58)),
    ((28, 22, 30), (58, 44, 42)),
    ((16, 30, 36), (34, 56, 62)),
    ((32, 26, 22), (62, 48, 38)),
]


def _gradient_frame(i: int, out_dir: Path) -> Path:
    """Render a vertical gradient placeholder frame."""
    path = out_dir / f"scene_{i:04d}.png"
    top, bottom = _GRADIENT_PALETTE[i % len(_GRADIENT_PALETTE)]

    img = Image.new("RGB", (1, VIDEO_HEIGHT))
    for y in range(VIDEO_HEIGHT):
        t = y / max(1, VIDEO_HEIGHT - 1)
        img.putpixel(
            (0, y),
            (
                int(top[0] + (bottom[0] - top[0]) * t),
                int(top[1] + (bottom[1] - top[1]) * t),
                int(top[2] + (bottom[2] - top[2]) * t),
            ),
        )
    img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.BILINEAR).save(path)
    return path


# ─────────────────────────────────────────────────────
# Motion
# ─────────────────────────────────────────────────────

def animate_scene(
    img_path: Path,
    out_path: Path,
    duration: float,
    effect: str = "zoom_in",
    fade: float = 0.0,
) -> Path:
    """Render one still into a moving clip with a Ken Burns move.

    `fade` adds a dip to black at both ends, which is how transitions are done
    here: an xfade chain across a hundred clips is fragile and slow to encode,
    while a per-clip fade costs nothing and reads the same at these durations.
    """
    frames = max(2, int(duration * FPS))
    w, h = VIDEO_WIDTH, VIDEO_HEIGHT

    if effect == "zoom_in":
        vf = (
            f"scale={int(w * 1.12)}:{int(h * 1.12)},"
            f"zoompan=z='1.12-0.12*on/{frames}':x='iw/2-(iw/zoom/2)'"
            f":y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={FPS}"
        )
    elif effect == "zoom_out":
        vf = (
            f"scale={int(w * 1.12)}:{int(h * 1.12)},"
            f"zoompan=z='1.0+0.12*on/{frames}':x='iw/2-(iw/zoom/2)'"
            f":y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={FPS}"
        )
    elif effect == "pan_left":
        vf = (
            f"scale={int(w * 1.15)}:{int(h * 1.15)},"
            f"zoompan=z=1.15:x='0.15*iw*(1-on/{frames})':y='ih*0.075'"
            f":d={frames}:s={w}x{h}:fps={FPS}"
        )
    else:  # pan_right
        vf = (
            f"scale={int(w * 1.15)}:{int(h * 1.15)},"
            f"zoompan=z=1.15:x='0.15*iw*on/{frames}':y='ih*0.075'"
            f":d={frames}:s={w}x{h}:fps={FPS}"
        )

    if fade > 0:
        fade_out_start = max(0.0, duration - fade)
        vf += (
            f",fade=t=in:st=0:d={fade:.2f}"
            f",fade=t=out:st={fade_out_start:.2f}:d={fade:.2f}"
        )

    run_cmd([
        "ffmpeg", "-loop", "1", "-i", str(img_path),
        "-vf", vf, "-t", f"{duration:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(out_path), "-y", "-loglevel", "quiet",
    ])
    return out_path
