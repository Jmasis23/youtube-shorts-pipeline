"""Long-form subtitles — an SRT sidecar, and optional burn-in.

Short-form burns word-popping karaoke captions into the frame because the video
is watched muted in a feed. Long-form is the opposite: it is watched with sound,
often on a TV, and permanently burned captions cannot be turned off. So the
default here is an SRT sidecar that drives YouTube's own CC track, with burn-in
available per format for the styles that want it (countdowns, mainly).

Cues are grouped for reading rather than for rhythm: break on sentence
punctuation, cap the line length, and never let a cue outstay its welcome.
"""

from pathlib import Path

from verticals.captions import _whisper_word_timestamps
from verticals.log import log

from .config import VIDEO_HEIGHT, VIDEO_WIDTH

# A cue that stays up longer than this reads as a stalled player.
MAX_CUE_SECONDS = 6.0
# A gap this long between words is a natural cue break.
CUE_GAP_SECONDS = 0.6
_SENTENCE_ENDS = (".", "!", "?", "…")


def generate_subtitles(
    audio_path: Path,
    work_dir: Path,
    lang: str = "en",
    words_per_line: int = 8,
    burn_in: bool = False,
    font_family: str = "Arial",
    font_size: int = 44,
) -> dict:
    """Transcribe the narration and write subtitle files.

    Returns {"srt_path": str, "ass_path": str | None, "cues": int}. An empty
    dict-ish result (no srt_path) means transcription was unavailable — the
    render continues without captions rather than failing the whole run.
    """
    log("Transcribing narration for subtitles (this is the slow stage)...")
    words = _whisper_word_timestamps(audio_path, lang)

    if not words:
        log("No word timestamps available — skipping subtitles")
        return {"srt_path": "", "ass_path": "", "cues": 0}

    cues = group_into_cues(words, words_per_line=words_per_line)
    log(f"Grouped {len(words)} words into {len(cues)} subtitle cues")

    srt_path = work_dir / f"subtitles_{lang}.srt"
    write_srt(cues, srt_path)

    result = {"srt_path": str(srt_path), "ass_path": "", "cues": len(cues)}

    if burn_in:
        ass_path = work_dir / f"subtitles_{lang}.ass"
        write_ass(
            cues, ass_path, font_family=font_family, font_size=font_size
        )
        result["ass_path"] = str(ass_path)

    return result


def group_into_cues(words: list[dict], words_per_line: int = 8) -> list[dict]:
    """Group word timestamps into readable subtitle cues.

    A cue is closed when any of these is true: it hits the word cap, the last
    word ended a sentence, the next word starts after a pause, or the cue has
    been on screen too long.
    """
    cues: list[dict] = []
    current: list[dict] = []

    for i, word in enumerate(words):
        current.append(word)

        text = word.get("word", "")
        is_last = i == len(words) - 1
        hit_cap = len(current) >= max(1, words_per_line)
        ends_sentence = text.endswith(_SENTENCE_ENDS)
        long_enough = (
            current[-1]["end"] - current[0]["start"] >= MAX_CUE_SECONDS
        )
        gap_ahead = (
            not is_last
            and words[i + 1]["start"] - word["end"] >= CUE_GAP_SECONDS
        )

        if is_last or hit_cap or ends_sentence or long_enough or gap_ahead:
            cues.append(
                {
                    "start": current[0]["start"],
                    "end": current[-1]["end"],
                    "text": " ".join(w["word"] for w in current).strip(),
                }
            )
            current = []

    return [c for c in cues if c["text"]]


def write_srt(cues: list[dict], out_path: Path) -> Path:
    """Write cues as an SRT file for upload to YouTube."""
    blocks = []
    for i, cue in enumerate(cues, 1):
        blocks.append(
            f"{i}\n{_srt_time(cue['start'])} --> {_srt_time(cue['end'])}\n"
            f"{cue['text']}\n"
        )
    out_path.write_text("\n".join(blocks), encoding="utf-8")
    log(f"SRT written: {out_path.name}")
    return out_path


def write_ass(
    cues: list[dict],
    out_path: Path,
    font_family: str = "Arial",
    font_size: int = 44,
    video_width: int = VIDEO_WIDTH,
    video_height: int = VIDEO_HEIGHT,
) -> Path:
    """Write cues as an ASS file for burn-in.

    Bottom-centred with an outline and a soft shadow — legible over any b-roll
    without the boxed-in look, and clear of YouTube's control bar.
    """
    margin_v = int(video_height * 0.08)
    header = f"""[Script Info]
Title: Longform Subtitles
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_family},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,120,120,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = [
        f"Dialogue: 0,{_ass_time(c['start'])},{_ass_time(c['end'])},"
        f"Default,,0,0,0,,{_escape_ass(c['text'])}"
        for c in cues
    ]
    out_path.write_text(header + "\n".join(events), encoding="utf-8")
    log(f"ASS written: {out_path.name}")
    return out_path


def _escape_ass(text: str) -> str:
    """Escape characters that ASS treats as markup."""
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _srt_time(seconds: float) -> str:
    """HH:MM:SS,mmm"""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    if ms == 1000:  # rounding carry
        ms, s = 0, s + 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _ass_time(seconds: float) -> str:
    """H:MM:SS.cc"""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
