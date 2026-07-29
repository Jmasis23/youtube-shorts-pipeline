# 03 — Faceless long-form documentary, full pipeline

A 14-minute 16:9 documentary from a one-line topic, using the `longform` engine.

**Needs:** an LLM provider (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, or Ollama), `GEMINI_API_KEY` for scene images and narration, `ffmpeg` on PATH, and YouTube OAuth if you want the upload step.

Narration defaults to Gemini TTS when a Gemini key is present, read in the voice and delivery style the format profile specifies — `documentary` uses Charon, instructed to read "measured, low-energy, letting the facts carry the weight". Override with `--voice edge` (free) or `--voice-id Sulafat`.

Without `GEMINI_API_KEY` every scene renders as a gradient placeholder. That is a deliberate mode — the whole pipeline still runs, so you can check pacing, chapters, and audio before paying for a hundred images.

> **On the transcripts below:** the commands, flags, log lines, and output shapes are real. The render path (narration chunking, chapter timing, scene planning, image fallback, clip encode, concat, ducking, loudness, subtitles) was verified end to end against ffmpeg with stubbed TTS. The specific titles, chapter names, and word counts in the LLM stages are illustrative — your topic and provider will produce different text.

---

## Stage 1 — Plan the chapters

```bash
python -m longform outline \
  --topic "How container shipping actually works" \
  --format documentary \
  --niche general \
  --minutes 14
```

```
  Researching topic via DuckDuckGo...
  Loaded format profile: documentary
  Planning 14-minute documentary outline (6 chapters)...
  Outline: 6 chapters, 2100 word budget

  Working title : The Box That Ate The Docks
  Format        : documentary / general
  Target        : 14 min (~2100 words)
  Thesis        : Container shipping is a standardisation story, not a boats story.

  Sections:
    00. Intro  [168w]
    01. Before The Box  [303w]
    02. Newark, 1956  [302w]
    03. The Standard Nobody Wanted  [302w] <- open loop payoff
    04. The Ports That Bet Wrong  [302w]
    05. What Moved Instead  [302w]
    06. The Second-Order World  [302w]
    99. Outro  [126w]

  Outline saved: ~/.verticals/longform/projects/1785298758.json
  Next: python -m longform script --project 1785298758
```

The word budgets come from `--minutes`, not from the model. The intro and outro are deliberately short — the first thirty seconds decide retention, and a long outro is where viewers leave.

**This is the checkpoint that matters.** Read the chapter jobs before spending on the script. If two chapters could be swapped without loss, re-run the outline or edit the project JSON directly.

---

## Stage 2 — Write the narration

```bash
python -m longform script --project 1785298758
```

```
  Writing 1/8: Intro
  Writing 2/8: Before The Box
  ...
  Writing 8/8: Outro
  Script complete: 8 sections, 2143 words (~14.3 min)

  Script: 2143 words (~14.3 min)
    Intro                                           171w
    Before The Box                                  308w
    Newark, 1956                                    299w
    The Standard Nobody Wanted                      311w
    The Ports That Bet Wrong                        295w
    What Moved Instead                              304w
    The Second-Order World                          329w
    Outro                                           126w

  Full text: ~/.verticals/longform/media/work_1785298758_en/script.txt
```

One LLM call per section, each carrying a rolling summary of the sections already written. A section that lands under 65% of its budget gets one automatic expansion pass, reported in the log.

Read `script.txt` now. Editing `sections[n].narration` in the project JSON and re-running `produce --force` re-narrates from your text.

---

## Stage 3 — Produce

```bash
python -m longform produce --project 1785298758 --workers 6
```

```
  Producing project 1785298758 [documentary]

  Narrating 1/8: Intro
  Generating en voiceover via Gemini TTS (voice: Charon)...
  Narrating 2/8: Before The Box
    Section split into 2 TTS chunks
  ...
  Narration assembled: 8 sections, 14.2 min total

  0:00 Intro
  1:08 Before The Box
  3:11 Newark, 1956
  5:12 The Standard Nobody Wanted
  7:11 The Ports That Bet Wrong
  9:14 What Moved Instead
  11:16 The Second-Order World
  13:38 Outro

  Planned 78 scenes across 8 sections
  78 scenes over 14.2 minutes (~11s each)
  Generating 78 scene images (6 at a time)...
    10/78 scene images ready
    ...
    78/78 scene images ready
  Rendering 78 scene clips (2 at a time)...
    78/78 clips rendered
  Concatenating 78 clips...
  Transcribing narration for subtitles (this is the slow stage)...
  Grouped 2143 words into 291 subtitle cues
  SRT written: subtitles_en.srt
  Final render (14.2 min) — this takes a while...
  Video rendered: ~/.verticals/longform/media/longform_1785298758_en.mp4

  Video: ~/.verticals/longform/media/longform_1785298758_en.mp4
```

Chapter timestamps are measured from the rendered audio, not estimated from word counts. If a chapter lands under YouTube's ten-second minimum you get a warning naming it before the description is built.

Everything here is cached. Re-running `produce` skips completed stages; individual sections, images, and clips are cached too, so an interrupted run resumes rather than restarting.

Iterating on visuals? `--no-captions` skips Whisper, which is the slowest stage on a long video.

---

## Stage 4 — Metadata

```bash
python -m longform metadata --project 1785298758
```

```
  Writing YouTube metadata...

  Title: The Steel Box That Rewired World Trade
  Alternatives:
    - How A Truck Driver Broke The World's Docks
    - Container Shipping: The Standard That Won

  Description (1180 chars):

    In 1956 a converted tanker left Newark with 58 boxes on deck...

    Chapters:
    0:00 Intro
    1:08 Before The Box
    ...

  Tags: shipping,logistics,containerization,trade,history,infrastructure,...
```

The description is assembled around the measured chapter block rather than generated as free text: intro paragraph above the fold, chapters next so they are reachable in one tap, body after.

---

## Stage 5 — Upload

```bash
python -m longform upload --project 1785298758 --privacy unlisted
```

```
  Generating thumbnail via Gemini Imagen...
  Uploading longform_1785298758_en.mp4...
  Upload progress: 100%
  Uploaded: https://youtu.be/XXXXXXXXXXX
  Captions uploaded.
  Thumbnail uploaded.

  Live (unlisted): https://youtu.be/XXXXXXXXXXX

  Pinned comment to post:
    Which port would you have bet on in 1958?
```

Uploads default to `private`. The pinned comment is printed for you to post — the YouTube API cannot pin a comment on your behalf.

---

## All of it in one command

```bash
python -m longform run \
  --topic "How container shipping actually works" \
  --format documentary --minutes 14 --privacy unlisted
```

Add `--script-only` to stop after stage 2, or `--no-upload` to stop after stage 4.

---

## Free path

```bash
python -m longform run \
  --topic "How container shipping actually works" \
  --format explainer --minutes 8 \
  --provider ollama --voice edge --no-upload
```

Ollama for the script, Edge TTS for narration, gradient scenes with no Gemini key. $0.00, and every stage still runs — enough to judge structure and pacing before spending anything. Add a Gemini key and drop `--voice edge` to get real scenes and Gemini narration.

---

## Cost levers

Images dominate. A 14-minute documentary at 11s per scene is ~78 images.

- `--scene-seconds 15` cuts that to ~57
- `--minutes 10` cuts it to ~55
- the prompt-hash cache under `~/.verticals/longform/cache/` makes re-renders free
- `--no-upload` first, then check the script, then spend
