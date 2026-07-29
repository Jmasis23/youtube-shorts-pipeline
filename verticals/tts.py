"""Multi-provider TTS — Gemini (Google GenAI), Edge TTS, ElevenLabs, MiniMax, 60db, macOS say.

Gemini TTS is the long-form default: natural narration, 30 voices, and it takes
a plain-language style instruction ("read this as a measured documentary
narrator"), which is what lets a format profile shape delivery and not just
word choice. Uses the same GEMINI_API_KEY as b-roll and thumbnails.
Edge TTS is the Shorts default: free, cross-platform, 300+ voices, no API key.
ElevenLabs is premium: most natural, requires API key.
MiniMax is an alternative paid provider with streaming TTS.
60db is an alternative paid provider with native Indic-language voices and a lower per-character cost.
macOS say is the last-resort fallback.
"""

import base64
import os
from pathlib import Path

import requests

from .config import (
    VOICE_ID_EN,
    VOICE_ID_HI,
    get_60db_key,
    get_elevenlabs_key,
    get_gemini_key,
    get_minimax_key,
    run_cmd,
)
from .log import log
from .retry import with_retry


# ─────────────────────────────────────────────────────
# Gemini TTS (Google GenAI) — natural narration, style-steerable
# ─────────────────────────────────────────────────────

# Preview TTS models get replaced roughly every few months; check
# https://ai.google.dev/gemini-api/docs/models for the current one if this
# starts 404ing.
GEMINI_TTS_MODEL = "gemini-3.1-flash-tts-preview"

# The prebuilt voices exposed by the Gemini speech models. Names are stable
# across the flash and pro TTS models.
GEMINI_TTS_VOICES = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
]

# Charon reads as informative and unhurried — the safest default for narration.
GEMINI_VOICE_DEFAULT = "Charon"

# The model returns raw little-endian 16-bit PCM, not a container format.
GEMINI_TTS_SAMPLE_RATE = 24000


@with_retry(max_retries=3, base_delay=2.0)
def _call_gemini_tts(
    text: str,
    voice_name: str,
    api_key: str,
    model: str = GEMINI_TTS_MODEL,
) -> tuple[bytes, int]:
    """Call the Gemini speech model and return (raw PCM bytes, sample rate)."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta"
        f"/models/{model}:generateContent"
    )
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}
            },
        },
    }
    r = requests.post(
        url, json=body, timeout=180,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    if r.status_code != 200:
        try:
            detail = r.json().get("error", {}).get("message", r.text[:200])
        except Exception:
            detail = r.text[:200]
        hint = ""
        if r.status_code == 403:
            hint = (
                " — check that GEMINI_API_KEY is an AI Studio key "
                "(https://aistudio.google.com/apikey), not a Vertex AI / "
                "service-account credential"
            )
        elif r.status_code == 429:
            hint = " — Gemini TTS rate limit; retrying with backoff"
        elif r.status_code == 404:
            hint = (
                f" — {model} may have been retired; check current model IDs "
                "at https://ai.google.dev/gemini-api/docs/models and update "
                "GEMINI_TTS_MODEL in verticals/tts.py"
            )
        raise RuntimeError(f"Gemini TTS {r.status_code}: {detail}{hint}")

    data = r.json()
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"]), _pcm_rate(inline.get("mimeType", ""))

    raise RuntimeError("No audio in Gemini TTS response")


def _pcm_rate(mime_type: str) -> int:
    """Pull the sample rate out of a mime type like `audio/L16;codec=pcm;rate=24000`."""
    for param in mime_type.split(";"):
        key, _, value = param.strip().partition("=")
        if key.strip().lower() == "rate":
            try:
                return int(value)
            except ValueError:
                break
    return GEMINI_TTS_SAMPLE_RATE


def _generate_gemini_tts(
    script: str,
    out_dir: Path,
    lang: str,
    voice_id: str = "",
    style_prompt: str = "",
    model: str = GEMINI_TTS_MODEL,
) -> Path:
    """Generate a voiceover with Gemini TTS.

    `style_prompt` is a plain-language delivery instruction prepended to the
    text. The model follows it and speaks only what comes after the colon, so
    a format profile can ask for "an unhurried documentary narrator" without
    that phrase ending up in the audio.
    """
    api_key = get_gemini_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    voice = voice_id or GEMINI_VOICE_DEFAULT
    prompt = f"{style_prompt.rstrip(':')}: {script}" if style_prompt else script

    out_path = out_dir / f"voiceover_{lang}.mp3"
    pcm_path = out_dir / f"voiceover_{lang}.pcm"

    log(f"Generating {lang} voiceover via Gemini TTS (voice: {voice})...")
    pcm, rate = _call_gemini_tts(prompt, voice, api_key, model)
    pcm_path.write_bytes(pcm)

    # The API returns headerless PCM; everything downstream expects MP3.
    run_cmd([
        "ffmpeg", "-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", str(pcm_path),
        "-c:a", "libmp3lame", "-q:a", "2",
        str(out_path), "-y", "-loglevel", "quiet",
    ])
    pcm_path.unlink(missing_ok=True)

    log(f"Gemini TTS voiceover saved: {out_path.name}")
    return out_path


# ─────────────────────────────────────────────────────
# Edge TTS — free, cross-platform, 300+ voices
# ─────────────────────────────────────────────────────

# Default Edge TTS voices per language
EDGE_VOICES = {
    "en": "en-US-GuyNeural",
    "hi": "hi-IN-MadhurNeural",
    "es": "es-MX-JorgeNeural",
    "pt": "pt-BR-AntonioNeural",
    "de": "de-DE-ConradNeural",
    "fr": "fr-FR-HenriNeural",
    "ja": "ja-JP-KeitaNeural",
    "ko": "ko-KR-InJoonNeural",
}


async def _edge_tts_generate(text: str, voice: str, output_path: Path):
    """Generate audio via edge-tts (async)."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def _generate_edge_tts(script: str, out_dir: Path, lang: str, voice_override: str = "") -> Path:
    """Generate voiceover via Edge TTS (free Microsoft voices)."""
    import asyncio

    voice = voice_override or EDGE_VOICES.get(lang[:2], EDGE_VOICES["en"])
    out_path = out_dir / f"voiceover_{lang}.mp3"

    log(f"Generating {lang} voiceover via Edge TTS (voice: {voice})...")

    try:
        # Handle event loop — works whether called from sync or async context
        try:
            loop = asyncio.get_running_loop()
            # Already in an async context, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    _edge_tts_generate(script, voice, out_path)
                )
                future.result(timeout=60)
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            asyncio.run(_edge_tts_generate(script, voice, out_path))

        log(f"Edge TTS voiceover saved: {out_path.name}")
        return out_path
    except Exception as e:
        raise RuntimeError(f"Edge TTS failed: {e}")


# ─────────────────────────────────────────────────────
# ElevenLabs — premium, most natural
# ─────────────────────────────────────────────────────

@with_retry(max_retries=3, base_delay=2.0)
def _call_elevenlabs(script: str, voice_id: str, api_key: str, settings: dict | None = None) -> bytes:
    """Call ElevenLabs TTS API and return audio bytes."""
    voice_settings = settings or {
        "stability": 0.4,
        "similarity_boost": 0.85,
        "style": 0.3,
        "use_speaker_boost": True,
    }
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": script,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": voice_settings,
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:200]}")
    return r.content


def _generate_elevenlabs(
    script: str, out_dir: Path, lang: str,
    voice_id: str = "", settings: dict | None = None
) -> Path:
    """Generate voiceover via ElevenLabs."""
    api_key = get_elevenlabs_key()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY not set")

    vid = voice_id or (VOICE_ID_HI if lang == "hi" else VOICE_ID_EN)
    out_path = out_dir / f"voiceover_{lang}.mp3"

    log(f"Generating {lang} voiceover via ElevenLabs (voice: {vid})...")
    audio_bytes = _call_elevenlabs(script, vid, api_key, settings)
    out_path.write_bytes(audio_bytes)
    log(f"ElevenLabs voiceover saved: {out_path.name}")
    return out_path


# ─────────────────────────────────────────────────────
# MiniMax TTS — AI-powered, supports streaming SSE
# ─────────────────────────────────────────────────────

MINIMAX_TTS_VOICES = [
    "English_Graceful_Lady",
    "English_Insightful_Speaker",
    "English_radiant_girl",
    "English_Persuasive_Man",
    "English_Lucky_Robot",
    "English_expressive_narrator",
]


@with_retry(max_retries=3, base_delay=2.0)
def _call_minimax_tts(text: str, voice_id: str, api_key: str, model: str = "speech-2.8-hd") -> bytes:
    """Call MiniMax TTS API (streaming SSE) and return mp3 audio bytes."""
    base_url = os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io")
    base_url = base_url.rstrip("/").removesuffix("/v1")

    r = requests.post(
        f"{base_url}/v1/t2a_v2",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "text": text,
            "stream": True,
            "voice_setting": {
                "voice_id": voice_id,
                "speed": 1,
                "vol": 1,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
        },
        stream=True,
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"MiniMax TTS {r.status_code}: {r.text[:200]}")

    audio_chunks: list[bytes] = []
    buffer = ""
    for raw in r.iter_content(chunk_size=None):
        if not raw:
            continue
        buffer += raw.decode("utf-8", errors="replace")
        lines = buffer.split("\n")
        buffer = lines.pop()
        for line in lines:
            if not line.startswith("data:"):
                continue
            json_str = line[5:].strip()
            if not json_str or json_str == "[DONE]":
                continue
            try:
                import json as _json
                event_data = _json.loads(json_str)
                audio_hex = event_data.get("data", {}).get("audio")
                if audio_hex:
                    audio_chunks.append(bytes.fromhex(audio_hex))
            except Exception:
                pass

    if not audio_chunks:
        raise RuntimeError("MiniMax TTS returned no audio data")
    return b"".join(audio_chunks)


def _generate_minimax(
    script: str, out_dir: Path, lang: str,
    voice_id: str = "", model: str = "speech-2.8-hd",
) -> Path:
    """Generate voiceover via MiniMax TTS."""
    api_key = get_minimax_key()
    if not api_key:
        raise RuntimeError("MINIMAX_API_KEY not set")

    vid = voice_id or MINIMAX_TTS_VOICES[0]
    out_path = out_dir / f"voiceover_{lang}.mp3"

    log(f"Generating {lang} voiceover via MiniMax TTS (voice: {vid})...")
    audio_bytes = _call_minimax_tts(script, vid, api_key, model)
    out_path.write_bytes(audio_bytes)
    log(f"MiniMax TTS voiceover saved: {out_path.name}")
    return out_path


# ─────────────────────────────────────────────────────
# 60db — Indic-language native, low cost
# ─────────────────────────────────────────────────────

# Documented default voice — "Zara" (Hindi female) per /default-voices.
VOICE_ID_60DB_DEFAULT = "fbb75ed2-975a-40c7-9e06-38e30524a9a1"


@with_retry(max_retries=3, base_delay=2.0)
def _call_60db(script: str, voice_id: str, api_key: str, settings: dict | None = None) -> bytes:
    """Call 60db /tts-synthesize and return raw audio bytes.

    Native 60db parameter ranges (per https://docs.60db.ai/api-reference/tts/text-to-speech):
        stability:  0..100 (lower = more expressive)
        similarity: 0..100 (voice match fidelity)
        speed:      0.5..2.0
    """
    s = settings or {}
    payload = {
        "text": script,
        "voice_id": voice_id,
        "enhance": bool(s.get("enhance", True)),
        "speed": float(s.get("speed", 1.0)),
        "stability": int(s.get("stability", 50)),
        "similarity": int(s.get("similarity", 75)),
        "output_format": "mp3",  # pinned — captions.py / assemble.py expect MP3
    }
    r = requests.post(
        "https://api.60db.ai/tts-synthesize",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=payload,
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"60db {r.status_code}: {r.text[:200]}")

    body = r.json()
    if not body.get("success", True) or not body.get("audio_base64"):
        raise RuntimeError(f"60db returned no audio: {body.get('message', 'unknown')}")
    try:
        return base64.b64decode(body["audio_base64"])
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"60db audio_base64 decode failed: {exc}") from exc


def _generate_60db(
    script: str, out_dir: Path, lang: str,
    voice_id: str = "", settings: dict | None = None
) -> Path:
    """Generate voiceover via 60db."""
    api_key = get_60db_key()
    if not api_key:
        raise RuntimeError("SIXTYDB_API_KEY not set")

    vid = voice_id or VOICE_ID_60DB_DEFAULT
    out_path = out_dir / f"voiceover_{lang}.mp3"

    log(f"Generating {lang} voiceover via 60db (voice: {vid})...")
    audio_bytes = _call_60db(script, vid, api_key, settings)
    out_path.write_bytes(audio_bytes)
    log(f"60db voiceover saved: {out_path.name}")
    return out_path


# ─────────────────────────────────────────────────────
# macOS say — last resort fallback
# ─────────────────────────────────────────────────────

def _generate_say(script: str, out_dir: Path) -> Path:
    """macOS 'say' fallback TTS."""
    out_path = out_dir / "voiceover_say.aiff"
    mp3_path = out_dir / "voiceover_say.mp3"
    run_cmd(["say", "-o", str(out_path), script])
    run_cmd([
        "ffmpeg", "-i", str(out_path), "-acodec", "libmp3lame",
        str(mp3_path), "-y", "-loglevel", "quiet",
    ])
    return mp3_path


# ─────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────

def get_tts_provider(name: str | None = None) -> str:
    """Resolve which TTS provider to use.

    Priority: explicit name > TTS_PROVIDER env > config.json > auto-detect.
    Auto-detect tries: edge_tts > minimax > elevenlabs > 60db > say.

    Gemini is deliberately not in the auto-detect chain: a GEMINI_API_KEY is
    already required for b-roll, so auto-selecting it would silently move every
    existing Shorts user onto paid narration. Ask for it — `--voice gemini`, or
    TTS_PROVIDER=gemini. The long-form engine requests it explicitly.
    """
    if name and name != "auto":
        return name.lower()

    from_env = os.environ.get("TTS_PROVIDER", "").lower()
    if from_env:
        return from_env

    from .config import load_config
    from_cfg = load_config().get("TTS_PROVIDER", "").lower()
    if from_cfg:
        return from_cfg

    # Auto-detect: Edge TTS first (free, cross-platform)
    try:
        import edge_tts  # noqa: F401
        return "edge"
    except ImportError:
        pass

    if get_minimax_key():
        return "minimax"

    if get_elevenlabs_key():
        return "elevenlabs"

    if get_60db_key():
        return "60db"

    # macOS say as last resort
    import shutil
    if shutil.which("say"):
        return "say"

    raise RuntimeError(
        "No TTS provider available. Install one:\n"
        "  pip install edge-tts  (free, recommended)\n"
        "  Set MINIMAX_API_KEY (AI-powered)\n"
        "  Set ELEVENLABS_API_KEY (premium)\n"
        "  Or use macOS (has built-in 'say')"
    )


def generate_voiceover(
    script: str,
    out_dir: Path,
    lang: str = "en",
    provider: str | None = None,
    voice_config: dict | None = None,
) -> Path:
    """Generate voiceover via the configured TTS provider.

    Args:
        script: The voiceover text.
        out_dir: Directory to save the audio file.
        lang: Language code (en, hi, es, etc.).
        provider: TTS provider name (edge, elevenlabs, say).
        voice_config: Optional voice config from niche profile.

    Returns:
        Path to the generated audio file.
    """
    provider = get_tts_provider(provider)
    voice_config = voice_config or {}

    if provider in ("gemini", "google", "genai"):
        try:
            return _generate_gemini_tts(
                script, out_dir, lang,
                voice_id=voice_config.get("voice_id", ""),
                style_prompt=voice_config.get("style_prompt", ""),
                model=voice_config.get("model", GEMINI_TTS_MODEL),
            )
        except Exception as e:
            log(f"Gemini TTS failed: {e}")
            log("Falling back to Edge TTS...")
            provider = "edge"

    if provider == "edge":
        voice_override = voice_config.get("voice_id", "")
        try:
            return _generate_edge_tts(script, out_dir, lang, voice_override)
        except Exception as e:
            log(f"Edge TTS failed: {e}")
            # Fall through to next provider
            if get_minimax_key():
                log("Falling back to MiniMax TTS...")
                provider = "minimax"
            elif get_elevenlabs_key():
                log("Falling back to ElevenLabs...")
                provider = "elevenlabs"
            elif get_60db_key():
                log("Falling back to 60db...")
                provider = "60db"
            else:
                log("Falling back to macOS say...")
                return _generate_say(script, out_dir)

    if provider == "minimax":
        try:
            return _generate_minimax(
                script, out_dir, lang,
                voice_id=voice_config.get("voice_id", ""),
                model=voice_config.get("model", "speech-2.8-hd"),
            )
        except Exception as e:
            log(f"MiniMax TTS failed: {e}")
            if get_elevenlabs_key():
                log("Falling back to ElevenLabs...")
                provider = "elevenlabs"
            elif get_60db_key():
                log("Falling back to 60db...")
                provider = "60db"
            else:
                log("Falling back to macOS say...")
                return _generate_say(script, out_dir)

    if provider == "elevenlabs":
        try:
            return _generate_elevenlabs(
                script, out_dir, lang,
                voice_id=voice_config.get("voice_id", ""),
                settings=voice_config.get("settings"),
            )
        except Exception as e:
            log(f"ElevenLabs failed: {e}")
            if get_60db_key():
                log("Falling back to 60db...")
                provider = "60db"
            else:
                log("Falling back to macOS say...")
                return _generate_say(script, out_dir)

    if provider == "60db":
        try:
            return _generate_60db(
                script, out_dir, lang,
                voice_id=voice_config.get("voice_id", ""),
                settings=voice_config.get("settings"),
            )
        except Exception as e:
            log(f"60db failed: {e}")
            log("Falling back to macOS say...")
            return _generate_say(script, out_dir)

    if provider == "say":
        return _generate_say(script, out_dir)

    raise ValueError(f"Unknown TTS provider: {provider}")
