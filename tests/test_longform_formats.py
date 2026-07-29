"""Tests for format profile loading and the prompt-context builders."""

import longform.formats as formats
from longform.formats import (
    get_voice_config,
    get_audio_config,
    get_caption_config,
    get_chapter_count,
    get_metadata_config,
    get_scene_seconds,
    get_structure_context,
    get_target_minutes,
    get_visual_config,
    list_formats,
    load_format,
)


class TestListAndLoad:
    def test_ships_the_documented_formats(self):
        names = list_formats()
        for expected in (
            "documentary", "explainer", "listicle",
            "story", "case_study", "video_essay",
        ):
            assert expected in names

    def test_load_returns_profile(self):
        profile = load_format("documentary")
        assert profile["name"] == "documentary"
        assert profile["display_name"] == "Documentary Deep Dive"

    def test_unknown_format_falls_back_to_explainer(self):
        assert load_format("no-such-format")["name"] == "explainer"

    def test_load_is_case_insensitive(self):
        assert load_format("DOCUMENTARY")["name"] == "documentary"

    def test_load_is_cached(self):
        formats._cache.clear()
        load_format("story")
        assert "story" in formats._cache

    def test_every_shipped_format_parses(self):
        for name in list_formats():
            profile = load_format(name)
            assert profile.get("script", {}).get("tone")
            assert profile.get("target_minutes")
            assert profile.get("chapters")


class TestOverrides:
    def test_target_minutes_from_profile(self):
        assert get_target_minutes(load_format("documentary")) == 16

    def test_target_minutes_override_wins(self):
        assert get_target_minutes(load_format("documentary"), 8) == 8

    def test_chapter_count_from_profile(self):
        assert get_chapter_count(load_format("listicle")) == 10

    def test_chapter_count_override_wins(self):
        assert get_chapter_count(load_format("listicle"), 5) == 5

    def test_scene_seconds_from_profile(self):
        # The countdown format cuts faster than the documentary.
        assert get_scene_seconds(load_format("listicle")) < get_scene_seconds(
            load_format("documentary")
        )


class TestStructureContext:
    def test_includes_the_arc_and_retention_rules(self):
        context = get_structure_context(load_format("documentary"))
        assert "CHAPTER ARC" in context
        assert "RETENTION MECHANICS" in context
        assert "NEVER USE THESE PHRASES" in context

    def test_includes_hook_patterns(self):
        assert "HOOK PATTERNS" in get_structure_context(load_format("explainer"))

    def test_empty_profile_does_not_crash(self):
        assert isinstance(get_structure_context({}), str)


class TestStageConfigs:
    def test_caption_defaults_to_no_burn_in(self):
        # Long-form ships an SRT sidecar rather than burning captions in.
        assert get_caption_config(load_format("documentary"))["burn_in"] is False

    def test_listicle_burns_captions_in(self):
        assert get_caption_config(load_format("listicle"))["burn_in"] is True

    def test_audio_config_has_ducking_defaults(self):
        audio = get_audio_config(load_format("explainer"))
        assert audio["music_volume"] > 0
        assert audio["duck_ratio"] > 1

    def test_visual_config_merges_defaults(self):
        visuals = get_visual_config(load_format("story"))
        assert visuals["prompt_suffix"]
        assert visuals["motion"]
        assert "fade_seconds" in visuals

    def test_visual_config_avoids_faces(self):
        # Faceless is a hard constraint of the tool, not a per-format choice.
        for name in list_formats():
            avoid = get_visual_config(load_format(name)).get("subjects", {}).get("avoid", [])
            assert any("face" in a.lower() for a in avoid), name

    def test_metadata_config_has_category(self):
        assert get_metadata_config(load_format("explainer"))["category_id"]


class TestVoiceConfig:
    def test_every_format_ships_a_gemini_voice_and_style(self):
        from verticals.tts import GEMINI_TTS_VOICES

        for name in list_formats():
            config = get_voice_config(load_format(name), provider="gemini")
            assert config["voice_id"] in GEMINI_TTS_VOICES, name
            assert config["style_prompt"], name

    def test_formats_use_distinct_voices(self):
        # A countdown and a documentary should not be read by the same voice.
        voices = {
            get_voice_config(load_format(n), provider="gemini")["voice_id"]
            for n in list_formats()
        }
        assert len(voices) == len(list_formats())

    def test_unknown_provider_yields_no_voice_id(self):
        config = get_voice_config(load_format("documentary"), provider="elevenlabs")
        assert not config.get("voice_id")
        # The style prompt is provider-independent and still comes through.
        assert config["style_prompt"]

    def test_empty_profile_does_not_crash(self):
        assert get_voice_config({}, provider="gemini") == {"style_prompt": ""}


class TestLongformVoiceResolution:
    def test_defaults_to_gemini_when_a_key_is_present(self, monkeypatch):
        from longform.__main__ import _resolve_tts_provider

        monkeypatch.delenv("TTS_PROVIDER", raising=False)
        monkeypatch.setattr("verticals.config.get_gemini_key", lambda: "present")
        assert _resolve_tts_provider(None) == "gemini"

    def test_falls_back_to_auto_detect_without_a_key(self, monkeypatch):
        from longform.__main__ import _resolve_tts_provider

        monkeypatch.delenv("TTS_PROVIDER", raising=False)
        monkeypatch.setattr("verticals.config.get_gemini_key", lambda: "")
        assert _resolve_tts_provider(None) is None

    def test_explicit_voice_flag_wins(self, monkeypatch):
        from longform.__main__ import _resolve_tts_provider

        monkeypatch.setattr("verticals.config.get_gemini_key", lambda: "present")
        assert _resolve_tts_provider("edge") == "edge"

    def test_env_var_is_left_to_the_shared_resolver(self, monkeypatch):
        from longform.__main__ import _resolve_tts_provider

        monkeypatch.setenv("TTS_PROVIDER", "elevenlabs")
        monkeypatch.setattr("verticals.config.get_gemini_key", lambda: "present")
        assert _resolve_tts_provider(None) is None

    def test_format_voice_overrides_the_niche(self):
        from verticals.niche import load_niche

        from longform.__main__ import _resolve_voice_config

        config = _resolve_voice_config(
            load_format("story"), load_niche("general"), "gemini", "en", None
        )
        assert config["voice_id"] == "Sulafat"
        assert "storyteller" in config["style_prompt"]

    def test_niche_fills_in_what_the_format_omits(self):
        from verticals.niche import load_niche

        from longform.__main__ import _resolve_voice_config

        # No format ships an edge_tts voice, so the niche's must come through.
        config = _resolve_voice_config(
            load_format("documentary"), load_niche("general"), "edge", "en", None
        )
        assert config["voice_id"] == "en-US-GuyNeural"

    def test_voice_id_override_beats_everything(self):
        from verticals.niche import load_niche

        from longform.__main__ import _resolve_voice_config

        config = _resolve_voice_config(
            load_format("story"), load_niche("general"), "gemini", "en", "Kore"
        )
        assert config["voice_id"] == "Kore"
