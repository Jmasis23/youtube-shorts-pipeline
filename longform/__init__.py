"""Longform — faceless long-form YouTube video engine.

Sibling to the `verticals` short-form engine. Where verticals produces a
60-second 9:16 clip from a single LLM call, longform produces an 8-30 minute
16:9 narrated video: a retention-engineered chapter outline, per-chapter
narration written with rolling context, one AI-generated scene every few
seconds, real chapter timestamps measured from the rendered audio, and a
description built around them.

Shared primitives (LLM routing, TTS providers, Whisper, YouTube upload,
API-key resolution) are imported from `verticals` rather than duplicated.
"""

__version__ = "1.0.0"
