---
name: verticals
description: "AI-native video engine with niche intelligence. Two engines: `verticals` takes a one-line topic and a niche profile and outputs a finished YouTube Short/Reel/TikTok with AI-generated b-roll, voiceover, burned-in captions, background music, and thumbnail; `longform` takes a topic and a format profile and outputs a faceless 8-30 minute 16:9 YouTube video with a two-pass chapter script, ~100 AI-generated scenes, measured chapter timestamps, and a chapter-built description. Supports multiple LLM providers (Claude, Gemini, GPT, Ollama), TTS providers (Edge TTS, ElevenLabs, MiniMax, 60db), 15+ content niches, and 6 long-form formats."
---

# Verticals v3

Two engines sharing one credential store, LLM router, TTS layer, and uploader.

**`verticals`** — vertical Shorts: topic + niche -> research -> script -> visuals -> voice -> captions -> music -> thumbnail -> upload.

**`longform`** — faceless long-form: topic + format -> outline -> per-chapter script -> narration -> scenes -> chapters -> metadata -> upload.

## Commands

```bash
# Shorts
python -m verticals run --topic "headline" --niche tech
python -m verticals run --discover --auto-pick --niche gaming
python -m verticals draft --topic "headline" --niche finance --provider gemini
python -m verticals produce --draft <path> --voice edge
python -m verticals topics --niche tech --limit 20
python -m verticals niches

# Long-form
python -m longform run --topic "topic" --format documentary --minutes 14
python -m longform outline --topic "topic" --format case_study
python -m longform script --project <id>
python -m longform produce --project <id> --scene-seconds 10
python -m longform import-script --file script.md --topic "topic"
python -m longform formats
python -m longform status --project <id>
```

## Long-form formats

explainer (10 min), documentary (16 min), listicle (12 min), story (18 min), case_study (13 min), video_essay (15 min). Format = structure; niche = subject flavour. They compose.

## Long-form flags

--format NAME: Format profile
--minutes N: Runtime target (3-60), drives the word budget
--chapters N: Body chapter count
--scene-seconds N: Seconds of narration per visual
--voice NAME: TTS provider; defaults to gemini (Google GenAI) when GEMINI_API_KEY is set, else edge
--voice-id NAME: Specific voice, e.g. Charon, Sulafat, Iapetus
--no-upload / --script-only: Stop `run` early
--force: Redo stages already marked done

Guide: references/longform.md

## Key flags

--niche NAME: Content niche (tech, gaming, finance, fitness, cooking, travel, etc.)
--provider NAME: LLM provider (claude, gemini, openai, ollama)
--voice NAME: TTS provider (edge, elevenlabs, minimax, 60db, say)
--platform NAME: Target platform (shorts, reels, tiktok, all)
--lang CODE: Language (en, hi, es, pt, de, fr, ja, ko)

## $0.00 mode

python -m verticals run --topic "X" --niche tech --provider ollama --voice edge

Docs: https://github.com/rushindrasinha/youtube-shorts-pipeline
Product: https://verticals.gg
