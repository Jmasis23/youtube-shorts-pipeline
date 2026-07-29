# Verticals v3

**The open source AI content engine with built-in niche intelligence.**

> Topic in. Published Short out. Any niche. ~$0.11 per video.
>
> **[Quickstart](#quickstart) · [Hosted Version](https://verticals.gg)**

> Repo note: the product is called **Verticals v3**. The GitHub repository is `youtube-shorts-pipeline`.

```
python -m verticals run --topic "Sam Altman just mass-fired 200 safety researchers" --niche tech
```

That one command researches the topic, writes a hook driven script tuned to tech YouTube, generates cinematic b roll, records a natural voiceover, burns in animated captions, adds mood matched background music, generates a thumbnail, and uploads it to YouTube. ~90 seconds of video, ~3 minutes of wall time, ~$0.11 in API costs.

## What Changed in v3

v2 was an esports news pipeline. v3 is a **general purpose content engine** that works for any niche, any topic, any creator.

The biggest change: **Niche Intelligence**. Every stage of the pipeline now reads from a niche profile that shapes script tone, visual style, caption aesthetics, music mood, and thumbnail strategy. Ship a cooking Short and it writes like a cooking creator, generates food photography b roll, and picks warm upbeat background music. Ship a true crime Short and the tone shifts to suspenseful, the visuals go dark and cinematic, and the music drops to ambient tension.

15 niches ship out of the box. Build your own in 5 minutes.

Other highlights: multi provider LLM support (Claude, Gemini, GPT, Ollama local), free TTS via Edge TTS, YouTube upload, topic discovery, resumable stages, and a local-first config model.

## Current Release: v3.1.0

v3.1.0 brings community-contributed providers and reliability fixes: MiniMax (LLM + TTS) and 60db (TTS) as optional providers, niche-aware caption fonts so CJK and other non-Latin scripts render correctly, a working `edge-tts` pin (6.x is rejected by Microsoft with 403s), and clearer errors for the most-reported setup problems.

Implemented today:

- research with DuckDuckGo plus optional source scraping
- script and metadata generation through Claude, Gemini, GPT, Ollama, MiniMax, LiteLLM, or Claude CLI
- b roll and thumbnail image generation through Gemini Imagen, with fallback frames
- voiceover through Edge TTS, ElevenLabs, MiniMax, 60db, or macOS `say`
- Whisper captions with ASS burn-in plus SRT export, niche-configurable fonts
- ffmpeg assembly with Ken Burns motion, background music, and voice ducking
- private-by-default YouTube upload

Not shipped yet: Gradio UI, Docker, Colab, TikTok/Reels/X upload, Pexels, Replicate, ComfyUI, and Kokoro TTS. Those are roadmap items, not current features.

## Long-Form Engine

The repo ships a second engine, `longform`, for faceless **8 to 30 minute 16:9** videos — the documentary, explainer, and video-essay side of a channel rather than the Shorts side.

```
python -m longform run --topic "How container shipping actually works" --format documentary --minutes 14
```

That command plans a chapter outline, writes the narration one chapter at a time, narrates it, generates a scene every ~10 seconds, measures the audio to produce real YouTube chapter timestamps, builds the description around them, and uploads.

It is a separate engine rather than a flag on `verticals` because a 15-minute video breaks in ways a 60-second one does not:

- **Two-pass script.** One LLM call cannot write 2,500 coherent words — it drifts, repeats, forgets its own cold open, and hits the output-token ceiling. Pass one plans the chapters and fixes a word budget per chapter from the runtime target. Pass two writes each chapter with a rolling summary of what came before.
- **Format profiles.** `formats/*.yaml` sits alongside `niches/*.yaml`. The niche says what the video is about; the format says how it is built — chapter arc, retention mechanics, where the open loop pays off. Six ship: `explainer`, `documentary`, `listicle`, `story`, `case_study`, `video_essay`.
- **Real chapters.** Timestamps come from the measured duration of each rendered section, then get validated against YouTube's rules (first at `0:00`, at least three, each at least 10s) before the description is written.
- **Scale.** ~100 scenes per video: images generated concurrently and cached by prompt hash, scene clips encoded once so the concat is a stream copy, sidechain music ducking instead of a per-speech-region volume envelope, and resume at the level of individual sections, images, and clips.
- **Faceless as a hard constraint.** No faces, no presenters, no identifiable people, no generated text or charts — enforced in every visual prompt regardless of format.
- **Gemini TTS narration.** Long-form defaults to Google GenAI speech (`gemini-3.1-flash-tts-preview`), using the `GEMINI_API_KEY` already needed for images. It takes a plain-language delivery instruction, so each format sets both a voice and how it is read — Charon reading a documentary "measured, letting the facts carry the weight", Laomedeia reading a countdown "brisk, lifting into each entry". Without a Gemini key it falls back to free Edge TTS.

Long-form defaults to an SRT sidecar rather than burned-in captions: Shorts are watched muted in a feed, long-form is watched with sound and often on a TV, and burned captions cannot be turned off.

Both engines share one credential store, one LLM router, one set of TTS providers, and one uploader. Full guide: [references/longform.md](references/longform.md).

### Web planner

`web/` is a Next.js app for the planning half: enter a topic, pick a format, get the chapter outline and the full narration in the browser, then download a `script.md` and render it with `longform import-script`. It deploys to Vercel with Root Directory set to `web` ([setup](web/README.md)).

It writes scripts but does not render video, and cannot: rendering needs ffmpeg, Whisper, and minutes of CPU per video. The architectural consequence is worth knowing if you fork it — **the browser drives the writing loop, one HTTP request per section**, so no serverless function ever runs longer than a single LLM call, and a failure on section six keeps the five already written. Format profiles are shared with the CLI through a generated module (`python3 scripts/gen_web_formats.py`), with a test that fails if it drifts.

```bash
python -m longform formats                          # list format profiles
python -m longform outline --topic "..." --format case_study
python -m longform script --project <id>            # review before rendering
python -m longform produce --project <id>
python -m longform import-script --file script.md --topic "..."   # bring your own
```

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        NICHE PROFILE                            │
│  Loaded once. Shapes every stage. 15 built in or bring your own │
└─────────────┬───────────────────────────────────────────────────┘
              │
              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ RESEARCH │→ │  SCRIPT  │→ │ VISUALS  │→ │  VOICE   │→ │ CAPTIONS │→ │ ASSEMBLE │→ UPLOAD
│          │  │          │  │          │  │          │  │          │  │          │
│ DuckDuck │  │ LLM with │  │ Gemini   │  │ ElevenLabs│  │ Whisper  │  │ ffmpeg   │
│ Go + web │  │ niche    │  │ fallback │  │ Edge TTS │  │ word     │  │ Ken Burns│
│ scraping │  │ persona  │  │ frames   │  │ say      │  │ level    │  │ + music  │
│          │  │ + hooks  │  │          │  │          │  │ ASS+SRT  │  │ ducking  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

**Stage by stage:**

**Research** — Searches DuckDuckGo (and optionally scrapes source URLs) for live facts. Every name, number, and claim in the final script traces back to this research. This is the anti hallucination gate: the LLM is instructed to use only facts from research data, never its training knowledge.

**Script** — An LLM (your choice of provider) writes a 60 to 90 second voiceover script using the niche profile's tone, pacing rules, and hook patterns. The profile tells the LLM things like "open with a question, not a statement" for tech niches or "open with a shocking statistic" for finance niches. Output includes the script, b roll image prompts, thumbnail prompt, and platform metadata for YouTube/TikTok/Instagram/X.

**Visuals** — Generates 3 b roll frames via Gemini Imagen, then auto crops them to 9:16 portrait. If image generation fails, the pipeline uses simple fallback frames so assembly can still complete. The niche profile shapes the visual vocabulary: a fitness niche generates gym and movement imagery, a science niche generates diagrams and lab visuals.

**Voice** — Text to speech via your configured provider: Edge TTS (free, cross platform, 300+ voices, **recommended default**), ElevenLabs (premium, most natural), or macOS `say` (fallback). The niche profile suggests voice characteristics (pace, energy, tone) but the final voice selection is yours.

**Captions** — Whisper generates word level timestamps. The pipeline produces both ASS (burned in with word by word yellow highlight) and SRT (uploaded to YouTube for closed captions). Caption styling follows the niche profile: bold energetic fonts for gaming, clean minimal for tech, warm handwritten feel for lifestyle.

**Assemble** — ffmpeg combines animated b roll (Ken Burns zoom/pan effects), voiceover, burned in captions, and background music with automatic voice ducking. Music selection is mood matched to the niche profile.

**Upload** — Publishes to YouTube (private by default) with title, description, tags, SRT captions, and AI generated thumbnail. TikTok and Instagram export coming in v3.1.

## Niche Intelligence

This is what makes Verticals different from every other AI video tool.

A niche profile is a YAML file that tells the pipeline how to think about content for a specific audience. It shapes every stage without requiring any prompt engineering from you.

```yaml
# niches/tech.yaml
name: tech
display_name: "Tech & AI News"

script:
  tone: "informed, slightly opinionated, conversational"
  pacing: "fast, dense with facts, no filler"
  hooks:
    - pattern: "contrarian_take"
      template: "Everyone is celebrating {topic}. Here's why that's a problem."
    - pattern: "breaking_news"
      template: "This just happened and nobody is talking about it."
    - pattern: "prediction"
      template: "{topic} changes everything. Here's what happens next."
    - pattern: "explainer"
      template: "Let me explain {topic} in 60 seconds because most people are getting this wrong."
    - pattern: "comparison"
      template: "{thing_a} vs {thing_b}. One of these wins and it's not even close."
  cta_variants:
    - "Follow for daily tech breakdowns."
    - "Subscribe. I cover AI news nobody else is talking about."
    - "Drop a comment: do you agree?"
  word_count: "150 to 170"
  forbidden: ["like and subscribe", "smash that bell", "what's up guys"]

visuals:
  style: "clean, minimal, dark backgrounds, neon accents"
  mood: "futuristic, sleek, professional"
  subjects: ["circuit boards", "code on screens", "server rooms", "product shots", "data visualizations"]
  avoid: ["stock photo people smiling at laptops", "generic office", "clipart"]

voice:
  pace: "slightly fast, ~160 wpm"
  energy: "confident, authoritative but not robotic"
  suggested_voices:
    edge_tts: "en-US-GuyNeural"
    elevenlabs: "JBFqnCBsd6RMkjVDRZzb"

captions:
  highlight_color: "#00FF88"
  font_weight: "bold"
  position: "lower_third"

music:
  mood: "ambient electronic, subtle energy, no lyrics"
  energy: "medium"

thumbnail:
  style: "dark background, bold white/green text, product or face focus"
  text_position: "left_aligned"
```

**15 built-in niches plus a general fallback:** tech, gaming, finance, fitness, cooking, travel, true_crime, science, politics, entertainment, sports, fashion, education, motivation, comedy, and general.

**Build your own** by copying any profile and editing it. Drop the YAML in `niches/` and reference it with `--niche your_niche_name`.

## Quickstart

### CLI

```bash
git clone https://github.com/rushindrasinha/youtube-shorts-pipeline.git
cd youtube-shorts-pipeline
pip install -r requirements.txt

python -m verticals run --topic "your topic" --niche tech
```

The old `--news` flag still works for backwards compatibility, but `--topic` is the recommended public API.

### Hosted Version

Use [verticals.gg](https://verticals.gg) if you want the workflow without local setup.

## Examples

Two worked end-to-end examples with real commands and the exact output to expect at each stage live in [`examples/`](examples/):

- [Tech news Short, full pipeline](examples/01-tech-news-short.md) — draft, produce, upload with the default providers
- [Zero-cost draft with topic discovery](examples/02-free-draft-discovery.md) — trending topics plus a local Ollama draft, no paid keys

## CLI Commands

### Full pipeline (topic to published Short)
```bash
python -m verticals run --topic "headline" --niche tech
python -m verticals run --topic "headline" --niche cooking --provider ollama
python -m verticals run --discover --niche gaming --auto-pick
```

### Individual stages
```bash
python -m verticals draft --topic "headline" --niche tech
python -m verticals produce --draft <path> --lang en
python -m verticals upload --draft <path> --lang en
python -m verticals topics --niche tech --limit 20
```

### Useful flags
```
--niche NAME         Niche profile (default: general)
--provider NAME      LLM provider: claude, gemini, openai, ollama, minimax (default: claude)
--voice NAME         TTS provider: edge, elevenlabs, minimax, 60db, say (default: edge)
--platform NAME      Draft target: shorts, reels, tiktok, all (default: shorts)
--lang CODE          Language: en, hi, es, pt, de, fr, ja, ko (default: en)
--dry-run            Draft only, skip produce and upload
--force              Redo all stages even if completed
--verbose            Debug logging
```

## Provider Support

### LLM (script generation)

| Provider | Cost | Setup | Notes |
|----------|------|-------|-------|
| **Claude** (Anthropic) | ~$0.02/script | `ANTHROPIC_API_KEY` | Best quality. Default. |
| **Gemini** (Google) | Free tier available | `GEMINI_API_KEY` | Good quality, generous free tier. |
| **GPT** (OpenAI) | ~$0.01/script | `OPENAI_API_KEY` | Solid alternative. |
| **Ollama** (local) | Free | Install Ollama + pull model | No API key needed. Quality varies by model. |
| **Claude CLI** | Free w/ Max sub | Install Claude Code | Uses Claude Max subscription, no API key. See [Claude authentication](#claude-authentication). |
| **MiniMax** | Pay-as-you-go | `MINIMAX_API_KEY` | OpenAI-compatible API. |

### TTS (voiceover)

| Provider | Cost | Setup | Notes |
|----------|------|-------|-------|
| **Edge TTS** | Free | None | **Recommended default.** 300+ voices, cross platform. |
| **ElevenLabs** | ~$0.05/video | `ELEVENLABS_API_KEY` | Most natural. Premium. |
| **MiniMax** | Pay-as-you-go | `MINIMAX_API_KEY` | Streaming TTS, English voices. |
| **60db** | Pay-as-you-go | `SIXTYDB_API_KEY` | Native Indic-language voices, low per-character cost. List voices: `python -m verticals voices --provider 60db`. |
| **macOS say** | Free | macOS only | Basic fallback. |

### Claude authentication

The `claude` provider works with any one of these, checked in order:

1. `ANTHROPIC_API_KEY` — a standard Anthropic API key from [console.anthropic.com](https://console.anthropic.com/settings/keys). This is **not** the same thing as a Claude Code OAuth token; the two are not interchangeable.
2. A logged-in Claude Code CLI (`claude login` with a Claude Max subscription). The pipeline shells out to `claude -p` and no API key is needed.
3. `CLAUDE_CODE_OAUTH_TOKEN` — a long-lived token from `claude setup-token`, with the `claude` CLI installed. Useful for CI and headless machines. The token is consumed by the CLI, not sent to the Anthropic API directly.

### Visuals (b roll)

| Provider | Cost | Setup | Notes |
|----------|------|-------|-------|
| **Gemini Imagen** | Free tier available | `GEMINI_API_KEY` | Default image provider. |
| **Fallback frames** | Free | None | Solid-color fallback frames if image generation fails. |

### Upload

| Platform | Status | Auth |
|----------|--------|------|
| **YouTube** | Stable | OAuth (setup wizard) |
| **TikTok** | v3.1 | Coming soon |
| **Instagram Reels** | v3.1 | Coming soon |
| **X (Twitter)** | v3.1 | Coming soon |

## $0.00 Mode (completely free)

Yes, you can run this with zero API spend:

```bash
python -m verticals draft \
  --topic "your topic" \
  --niche tech \
  --provider ollama
```

This creates the script and metadata with a local LLM. Full video production still needs visuals, TTS, captions, and ffmpeg; Edge TTS is free, while Gemini visuals require `GEMINI_API_KEY`.

## Configuration

All keys stored in `~/.verticals/config.json` with 0600 permissions:

| Variable | Required | Used By |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | If using Claude API | Script generation |
| `CLAUDE_CODE_OAUTH_TOKEN` | If using Claude CLI headless | Script generation (via `claude` CLI) |
| `GEMINI_API_KEY` | If using Gemini visuals/LLM | B roll + thumbnails |
| `OPENAI_API_KEY` | If using GPT | Script generation |
| `ELEVENLABS_API_KEY` | If using ElevenLabs | Premium voiceover |
| `MINIMAX_API_KEY` | If using MiniMax | Script generation + voiceover |
| `SIXTYDB_API_KEY` | If using 60db | Voiceover |

Environment variables override config file values.

Note on `GEMINI_API_KEY`: it must be an AI Studio key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Vertex AI or service-account credentials fail with `403: Method doesn't allow unregistered callers`. The same 403 appears when the key is simply not set in the environment the pipeline runs in (a common cause inside Docker — pass it with `docker run -e GEMINI_API_KEY=...`).

## Topic Discovery

Discover trending topics from multiple sources, filtered by niche relevance:

```bash
python -m verticals topics --niche tech --limit 20
```

| Source | Method | Auth | Niche Filtering |
|--------|--------|------|-----------------|
| Reddit | `.json` API | None | Subreddit mapping per niche |
| RSS | feedparser | None | Configurable feeds per niche |
| Google Trends | pytrends | None | Geo + category filtering |
| Twitter/X | Public API | Optional | Keyword filtering |
| TikTok | Apify | Optional | Hashtag mapping |
| YouTube Trending | RSS/API | None | Category mapping |
| Hacker News | API | None | Tech/startup default |

Configure per niche in your profile:
```yaml
# In niches/tech.yaml
discovery:
  reddit: ["technology", "artificial", "MachineLearning", "singularity"]
  rss: ["https://hnrss.org/frontpage", "https://techcrunch.com/feed"]
  google_trends_category: "t"
  youtube_trending_category: "28"
```

## Cost Per Video

Shorts:

| Configuration | Cost |
|---------------|------|
| **Premium** (Claude + Gemini + ElevenLabs) | ~$0.11 |
| **Budget** (Gemini + Gemini + Edge TTS) | ~$0.04 |
| **Draft-only local** (Ollama) | $0.00 |
| **Voice-only free path** (Edge TTS) | $0.00 for voice generation |

Long-form is dominated by scene images, then narration. A 14-minute documentary at 11s per scene is ~78 images and ~13,000 TTS characters. Raise `--scene-seconds`, lower `--minutes`, or lean on the prompt-hash image cache to bring that down; `--provider ollama --voice edge` with no Gemini key runs the whole pipeline at $0.00 with gradient placeholder scenes.

## Quality Limits

Verticals is built for repeatable short-form production, not for replacing an editor on story-led creative work.

It works best for:

- news explainers
- niche trend breakdowns
- list-style educational Shorts
- fast social experiments where volume matters

It is not ideal for:

- cinematic storytelling
- creator personality pieces
- videos that require taste, live footage, or strong art direction
- factual topics where the research source quality is weak

Use `draft --dry-run` or `run --dry-run` when testing a new niche. The most important human checkpoint is the draft: hook, factual claims, and whether the video has a real reason to exist.

## Distribution Loop

The pipeline is only the production layer. The useful operating loop is:

- Pick a niche with existing short-form demand.
- Generate and review a small batch of Shorts.
- Publish consistently on the platforms where that niche already moves.
- Use one clear call to action: free resource, newsletter, waitlist, or product.
- Read performance weekly, then tighten the niche profile and hooks.

This repo lowers the cost of testing. It does not remove the need for niche selection, distribution taste, or a real conversion path.

## Project Structure

```
verticals/
├── verticals/
│   ├── __main__.py            # CLI entry point
│   ├── config.py              # Keys, paths, setup wizard
│   ├── niche.py               # Niche profile loader
│   ├── llm.py                 # Claude / Gemini / GPT / Ollama
│   ├── research.py            # DuckDuckGo research gate
│   ├── draft.py               # Script generation with niche intelligence
│   ├── broll.py               # Gemini image generation + Ken Burns
│   ├── tts.py                 # ElevenLabs / Edge / say
│   ├── captions.py            # Whisper + ASS/SRT
│   ├── music.py               # Track selection + ducking
│   ├── assemble.py            # ffmpeg final assembly
│   ├── thumbnail.py           # Thumbnail generation + text overlay
│   ├── upload.py              # YouTube upload
│   ├── topics/                # Multi source topic engine
│   ├── state.py               # Resume capability
│   ├── retry.py               # Exponential backoff
│   └── log.py                 # Structured logging
├── longform/                  # Long-form engine (8 to 30 min, 16:9)
│   ├── __main__.py            # CLI entry point
│   ├── config.py              # Landscape constants, pacing math, paths
│   ├── formats.py             # Format profile loader
│   ├── outline.py             # Pass one: chapter plan + word budgets
│   ├── script.py              # Pass two: per-chapter narration
│   ├── narration.py           # Chunked TTS per section + measured timings
│   ├── chapters.py            # YouTube chapter markers + validation
│   ├── visuals.py             # Scene planning, 16:9 images, Ken Burns
│   ├── subtitles.py           # SRT sidecar + optional burn-in
│   ├── assemble.py            # Concat, sidechain ducking, loudness, render
│   ├── metadata.py            # Title, description with chapters, tags
│   ├── project.py             # Resumable project state
│   └── util.py                # JSON parsing, chunking, timestamps
├── web/                       # Next.js planner + landing page (Vercel)
│   ├── app/                   # pages and the two API routes
│   ├── components/            # planner client, chapter strip, sections
│   └── lib/                   # generated formats, prompts, budgets, LLM router
├── formats/                   # 6 long-form format profiles
│   ├── explainer.yaml
│   ├── documentary.yaml
│   ├── listicle.yaml
│   ├── story.yaml
│   ├── case_study.yaml
│   └── video_essay.yaml
├── niches/                    # 15 built in niche profiles
│   ├── tech.yaml
│   ├── gaming.yaml
│   ├── finance.yaml
│   ├── fitness.yaml
│   ├── cooking.yaml
│   ├── travel.yaml
│   ├── true_crime.yaml
│   ├── science.yaml
│   ├── politics.yaml
│   ├── entertainment.yaml
│   ├── sports.yaml
│   ├── fashion.yaml
│   ├── education.yaml
│   ├── motivation.yaml
│   ├── comedy.yaml
│   └── general.yaml           # Default fallback
├── tests/
├── scripts/
│   └── setup_youtube_oauth.py
├── references/
│   ├── setup.md
│   ├── longform.md
│   └── troubleshooting.md
├── pyproject.toml
└── requirements.txt
```

## Testing

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
```

## Security

All security measures from v2 carry forward, plus:

**Credential storage:** Config and tokens use 0600 permissions via atomic `os.open()`.
**API key handling:** All providers send keys via headers, never URL parameters.
**Upload privacy:** YouTube uploads default to private.
**Prompt injection:** Research snippets truncated to 300 chars with boundary markers. LLM output fields are type checked before use.
**OAuth scopes:** Minimum required scopes per platform.
**Niche profiles:** YAML parsed with safe_load (no code execution).
**Dependency pinning:** Compatible release bounds on all packages.

## Roadmap

**v3.0** (this release)
  Niche intelligence, multi provider LLM support, Edge TTS default, topic discovery, resumable stages, YouTube upload

**v3.1** (planned)
  TikTok/Instagram/X upload, multi language niche profiles, A/B script variants (generate 2, pick better), scheduled batch production

**v3.2** (planned)
  Analytics integration (which Shorts performed best), niche profile auto tuning based on performance data, series support (multi episode narrative arcs)

**Later**
  Web UI, Docker, Google Colab, additional visual providers, stock footage fallback

## Built By

**[Dr Rushindra Sinha](https://github.com/rushindrasinha)** — MD, Stanford GSB, Full Stack Developer.

Built the first game server at 17 (went #1 globally, acquired before finishing med school). Co-founded [Global Esports](https://globalesports.in) — South Asia's only Valorant Champions Tour Pacific franchise. Now building AI tools for creators and operators at [aarees.com](https://aarees.com).

Follow: [@irushi](https://twitter.com/irushi) on X · [@rushindrasinha](https://instagram.com/rushindrasinha) on Instagram

---

## More From This Stack

| Product | What it does |
|---------|-------------|
| [**verticals.gg**](https://verticals.gg) | Hosted version of this pipeline — no setup, no terminal, just results |
| [**thumbnail.gg**](https://thumbnail.gg) | AI thumbnail generation with deep niche intelligence and CTR optimization |
| [**aarees.com**](https://aarees.com) | The AI agent platform powering both products |
| [**Global Esports**](https://globalesports.in) | South Asia's VCT Pacific franchise — where the esports niche profile was battle-tested |

---

## License

MIT
