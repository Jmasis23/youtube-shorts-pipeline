# Longform — faceless long-form YouTube videos

`longform` is the long-form engine in this repo. Where `verticals` produces a
60-second 9:16 Short, `longform` produces an 8–30 minute 16:9 narrated video:
outline, script, narration, b-roll, chapters, metadata, upload.

```bash
python -m longform run \
  --topic "How container shipping actually works" \
  --format documentary --niche general --minutes 14
```

Both engines share one credential store (`~/.verticals/config.json`), one LLM
router, one set of TTS providers, and one YouTube uploader. Long-form artifacts
live under `~/.verticals/longform/`.

---

## Why long-form is a different tool

A Short is one LLM call and three images. A 15-minute video is not that at
scale — it breaks in specific ways that the short-form pipeline has no reason to
handle:

| | Shorts (`verticals`) | Long-form (`longform`) |
|---|---|---|
| Script | one call, ~150 words | two passes, one call per section, ~2,500 words |
| Coherence | not a problem | every section is written with the previous ones in context |
| Visuals | 3 frames | 60–150 scenes, generated concurrently and cached |
| Audio | one TTS call | chunked per section, concatenated, measured |
| Chapters | n/a | measured from the rendered audio, validated against YouTube's rules |
| Captions | burned in, word-popping | SRT sidecar by default; burn-in is per format |
| Voice | Edge TTS by default | Gemini TTS by default, steered by a per-format delivery instruction |
| Music | scripted volume envelope | sidechain ducking |
| Resume | per stage | per stage *and* per section, image, and clip |

The two-pass script is the core of it. Asking one call for 2,500 words gets you
something that drifts, repeats itself, forgets its own cold open, and hits the
output-token ceiling anyway. Pass one plans the chapters and fixes a word budget
per chapter from the runtime target. Pass two writes each chapter against that
plan with a rolling summary of what has already been said.

---

## Formats

A **niche** (`niches/*.yaml`, shared with the shorts engine) says what the video
is about — tone, visual vocabulary, music mood, voice. A **format**
(`formats/*.yaml`) says how a long video is *built* — chapter count, what each
chapter has to accomplish, where the open loop goes, how often to re-hook.

They compose: `--format documentary --niche tech` writes a documentary about
tech.

```bash
python -m longform formats
```

| Format | Default | Shape |
|---|---|---|
| `explainer` | 10 min, 5 ch | One question, answered in layers. The default. |
| `documentary` | 16 min, 6 ch | Evidence-led investigation, chronological, restrained. |
| `listicle` | 12 min, 10 ch | Ranked countdown, each entry a mini-story. Burns captions in. |
| `story` | 18 min, 5 ch | Narrative in acts — protagonist, want, obstacle, cost. |
| `case_study` | 13 min, 6 ch | How a company made or lost money. Numbers-led. |
| `video_essay` | 15 min, 5 ch | An argument, including the objection you can't fully answer. |

Each profile carries a chapter arc, retention mechanics, cold-open hook
patterns, forbidden phrases, visual direction, scene pacing, audio ducking, and
a YouTube category. Copy one and edit it to make your own — the loader picks up
any `formats/*.yaml`.

---

## Faceless is a hard constraint

Every visual prompt is generated under rules that are appended to the prompt and
cannot be overridden by a format profile:

- no faces, portraits, presenters, or talking heads
- no identifiable real people; a person in frame is distant, silhouetted, or
  cropped below the shoulders
- no legible text, signage, logos, or UI — generated text renders as garbage
- no charts or diagrams — generated ones are wrong and unreadable

Every shipped format's `visuals.subjects.avoid` list also names faces
explicitly, and there is a test asserting that stays true.

---

## Pipeline

```
outline ──► script ──► narration ──► scenes ──► images ──► clips ──► subtitles ──► assemble ──► metadata ──► thumbnail ──► upload
   │           │            │           │          │          │           │             │            │
 1 call    1 call per   chunked TTS  planned    concurrent  ffmpeg     whisper      concat +     built on
           section      per section  from       + cached    Ken Burns  SRT (+ASS)   duck +       measured
                        + measured   measured                                       loudnorm     chapters
```

Every stage records its artifacts in the project JSON. Re-running `produce`
skips what is already done; `--force` redoes everything.

### Stage notes

**narration** — synthesized per section, and within a section in ~1,200-char
sentence-aligned chunks (ElevenLabs caps around 5k, Edge TTS gets flaky well
before that). Sections stay separate files on purpose: measuring each one is
what produces the chapter timestamps. Concatenation re-encodes rather than
stream-copying, because a mid-run provider fallback can change sample rate and a
copy-concat of mismatched streams drifts out of sync with the captions.

Long-form defaults to **Gemini TTS** (Google GenAI) when `GEMINI_API_KEY` is set
— see [Voice](#voice) below. Without a key it falls back to the shared
auto-detect chain, which starts at free Edge TTS.

**scenes** — planned against *measured* section durations, so visuals stay locked
to narration even when a section runs long. The silence between sections is
absorbed into the preceding scene rather than dropped, which is what stops the
visuals creeping ahead of the audio over a 15-minute runtime.

**images** — generated concurrently (`--workers`, default 4) and cached by prompt
hash under `~/.verticals/longform/cache/`, so a re-render costs nothing and a
partial failure does not restart the batch. A failed image degrades to a
generated gradient; one dead frame in a hundred is not worth losing the render.
Without `GEMINI_API_KEY` every scene is a gradient, which keeps the pipeline
runnable end to end so you can check timings, chapters, and audio before paying
for images.

**clips** — each scene encoded once with identical settings, so the concat is a
stream copy. Transitions are a per-clip dip to black (`--fade`), not an `xfade`
chain: a hundred-clip xfade graph is slow and fragile and reads the same at these
durations.

**assemble** — one final pass mixes audio, optionally burns subtitles, and
normalises to −16 LUFS. It also pads the video to the narration: per-scene frame
rounding accumulates across a hundred clips, and a video that ends a second
early truncates the outro. Music is ducked by sidechain compression rather than a
scripted volume envelope — on a 15-minute track an envelope means hundreds of
`between()` terms and only ever approximates where the speech actually is.

**metadata** — the description is *assembled* around the measured chapter block
rather than generated as free text. The intro paragraph sits above the fold, the
chapters come next, the body follows.

---

## Voice

Narration defaults to **Gemini TTS** (Google GenAI) — `gemini-3.1-flash-tts-preview`,
using the same `GEMINI_API_KEY` already required for scene images. Two reasons
it is the long-form default rather than Edge:

1. It holds up over fifteen minutes. Edge TTS is fine for a 60-second Short; the
   flatness becomes obvious at length.
2. It takes a plain-language **delivery instruction**, so a format profile can
   shape how narration is *read*, not just how it is written. The instruction is
   prepended to the text and the model follows it without speaking it.

Each shipped format sets its own voice and instruction:

| Format | Voice | Delivery |
|---|---|---|
| `explainer` | Iapetus | clear, unhurried, warm but not chatty |
| `documentary` | Charon | restrained, low-energy, never dramatising |
| `listicle` | Laomedeia | brisk, lifting into each entry, without shouting |
| `story` | Sulafat | warm, close-mic, patient with pauses |
| `case_study` | Sadaltager | precise, even, slightly dry, emphasising figures |
| `video_essay` | Algieba | reflective, pausing where the argument turns |

```yaml
# formats/<name>.yaml
voice:
  style_prompt: >
    Read this as a restrained documentary narrator — measured, low-energy,
    letting the facts carry the weight, never dramatising
  suggested_voices:
    gemini:
      en: "Charon"
```

Thirty prebuilt voices are available (`verticals.tts.GEMINI_TTS_VOICES`).
Override per run with `--voice-id Sulafat`, or switch provider entirely with
`--voice edge` / `--voice elevenlabs` / `--voice 60db`. Format voice settings win
over the niche's; the niche fills in whatever the format leaves out, so
non-Gemini providers still get their voice from the niche profile as before.

The Gemini API returns headerless 16-bit PCM, which the provider converts to MP3
with ffmpeg before the rest of the pipeline sees it. A Gemini TTS failure falls
back to Edge TTS rather than failing the render.

The Shorts engine is unchanged: Gemini is not in its auto-detect chain, because a
`GEMINI_API_KEY` is already required for b-roll and auto-selecting it would move
existing users onto paid narration silently. Opt in with `--voice gemini` or
`TTS_PROVIDER=gemini`.

## Chapters

Chapters are the highest-leverage long-form feature: a navigable table of
contents under the player, key moments in search, and better session time on
anything over ten minutes.

YouTube only activates them when the first timestamp is `0:00`, there are at
least three, and each runs at least ten seconds. `longform` builds them from
measured audio and validates them before writing the description — if a chapter
is too short you get a warning naming it, rather than a silently inert block:

```
  Chapter warnings:
    - chapter 'Quick Aside' runs 7s — under YouTube's 10s minimum
```

Fix it by merging beats in the outline or raising `--minutes`.

---

## Commands

```bash
# Plan the chapters (pass one)
python -m longform outline --topic "..." --format documentary --minutes 16

# Write the narration (pass two)
python -m longform script --project 1785298758

# Narrate, generate scenes, render
python -m longform produce --project 1785298758

# Title, description with chapters, tags, pinned comment
python -m longform metadata --project 1785298758

# Upload
python -m longform upload --project 1785298758 --privacy unlisted

# All of the above
python -m longform run --topic "..." --format case_study --no-upload

# Bring your own script
python -m longform import-script --file script.md --topic "..." --format story

# Housekeeping
python -m longform formats
python -m longform projects
python -m longform status --project 1785298758
```

### Flags worth knowing

| Flag | Effect |
|---|---|
| `--minutes N` | Runtime target; drives the word budget. 3–60. |
| `--chapters N` | Body chapter count, overriding the format's default. |
| `--scene-seconds N` | Seconds of narration per visual. Lower = more images = more cost. |
| `--voice NAME` | `gemini` (default with a Gemini key), `edge`, `elevenlabs`, `minimax`, `60db`, `say`. |
| `--voice-id NAME` | Specific voice for that provider, e.g. `Sulafat`. |
| `--workers N` | Concurrent image generations (default 4). |
| `--render-workers N` | Concurrent ffmpeg scene encodes (default 2). |
| `--fade N` | Dip-to-black seconds at each scene edge. `0` = hard cuts. |
| `--burn-captions` / `--no-captions` | Override the format's caption default. |
| `--no-music` / `--music PATH` | Background bed control. |
| `--no-loudnorm` | Skip loudness normalisation. |
| `--no-research` | Skip live search; claims stay general. |
| `--script-only` / `--no-upload` | Stop `run` early. |
| `--force` | Redo stages already marked done. |
| `--privacy` | `private` (default), `unlisted`, `public`. |

### Bringing your own script

`import-script` splits on `## Heading` lines, using the heading as the chapter
title; without headings it splits on blank lines into `--chapters` sections. It
then generates visual prompts per section, the same way the writing path does —
an imported script gets b-roll as relevant as a generated one.

```markdown
## Intro
The cold open goes here.

## Before The Box
Break-bulk cargo took days to load...
```

---

## Cost and runtime

Dominated by images, then by the final encode.

A 14-minute documentary at 11s per scene is ~77 scenes:

| | |
|---|---|
| LLM (outline + 7 sections + metadata) | ~9 calls |
| Images | ~77 |
| TTS characters | ~13,000 |
| Wall time | image generation, then ~2–6 min of encode on a laptop CPU |

Levers: raise `--scene-seconds` (fewer images), lower `--minutes`, reuse the
prompt cache across re-renders, or run `--no-upload` and check the script before
spending on images. The free path — Ollama for the LLM, Edge TTS for voice, no
Gemini key for gradient scenes — costs $0.00 and still exercises every stage.

---

## Where things live

```
~/.verticals/
├── config.json                  # shared with the shorts engine
└── longform/
    ├── projects/<id>.json        # outline, script, stage state, metadata
    ├── media/
    │   ├── work_<id>_en/         # narration, frames, clips, subtitles
    │   └── longform_<id>_en.mp4  # the deliverable
    └── cache/<hash>.png          # prompt-addressed image cache
```

The project JSON is the whole record of a video. It is safe to read, diff, and
hand-edit between stages — editing `sections[n].narration` and re-running
`produce --force` re-narrates from your text.

---

## Troubleshooting

**"No LLM provider found"** — set `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, or
`OPENAI_API_KEY`, or run Ollama locally, or log in to Claude Code. Same
resolution order as the shorts engine.

**Sections come back short** — a section under 65% of its word budget gets one
automatic expansion pass. If it is still short, the model is thin on the topic:
narrow it, or lower `--minutes`.

**Chapters not showing on YouTube** — read the chapter warnings from `produce`.
All three of YouTube's rules have to hold.

**Subtitles are not burned in** — the format may set `burn_in: false` (most do,
deliberately). Force it with `--burn-captions`. If the log says the ffmpeg build
has no libass, the SRT sidecar still uploads.

**Video ends before the narration** — should not happen; the final pass measures
both and pads. If you see it, check that `ffprobe` is on `PATH`.

**Whisper is slow** — it is the slowest stage on a long video. `--no-captions`
skips it while you are iterating on visuals.

**Gemini TTS 429s** — the free tier's per-minute limit is low and a long script
is many chunks. The provider retries with backoff; if it keeps failing, use
`--voice edge` for the draft pass and switch back for the final render.

**The delivery instruction is being read aloud** — the model normally follows the
style prefix silently. If it leaks into the audio, shorten `style_prompt` in the
format profile to a single clause.
