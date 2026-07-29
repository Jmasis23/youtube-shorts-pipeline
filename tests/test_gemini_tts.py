"""Tests for the Gemini (Google GenAI) TTS provider."""

import base64
from pathlib import Path

import pytest

from verticals import tts
from verticals.tts import (
    GEMINI_TTS_MODEL,
    GEMINI_VOICE_DEFAULT,
    _generate_gemini_tts,
    _pcm_rate,
    generate_voiceover,
    get_tts_provider,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def audio_payload(pcm: bytes, mime="audio/L16;codec=pcm;rate=24000"):
    return {
        "candidates": [
            {"content": {"parts": [
                {"inlineData": {"mimeType": mime,
                                "data": base64.b64encode(pcm).decode()}}
            ]}}
        ]
    }


def stub_encode(calls):
    """Stand in for the ffmpeg PCM->MP3 encode, writing the output file."""
    def fake_run_cmd(cmd, **kwargs):
        calls["cmd"] = cmd
        out = next(arg for arg in cmd if str(arg).endswith(".mp3"))
        Path(out).write_bytes(b"ID3fake-mp3")
    return fake_run_cmd


@pytest.fixture(autouse=True)
def no_retry_backoff(monkeypatch):
    """Keep the retry decorator's failure paths from sleeping through the suite."""
    monkeypatch.setattr("verticals.retry.time.sleep", lambda _: None)


@pytest.fixture
def captured(monkeypatch, tmp_path):
    """Capture the outgoing request and stub out the ffmpeg conversion."""
    calls = {}

    def fake_post(url, json=None, timeout=None, headers=None):
        calls["url"] = url
        calls["body"] = json
        calls["headers"] = headers
        return FakeResponse(payload=audio_payload(b"\x00\x01" * 1000))

    monkeypatch.setattr(tts.requests, "post", fake_post)
    monkeypatch.setattr(tts, "run_cmd", stub_encode(calls))
    monkeypatch.setattr(tts, "get_gemini_key", lambda: "test-key")
    return calls


class TestGeminiTts:
    def test_generates_an_mp3(self, captured, tmp_path):
        out = _generate_gemini_tts("Hello there.", tmp_path, "en")
        assert out.exists()
        assert out.suffix == ".mp3"

    def test_uses_the_tts_model_and_audio_modality(self, captured, tmp_path):
        _generate_gemini_tts("Hello.", tmp_path, "en")
        assert GEMINI_TTS_MODEL in captured["url"]
        assert captured["body"]["generationConfig"]["responseModalities"] == ["AUDIO"]

    def test_sends_the_key_as_a_header_not_a_query_param(self, captured, tmp_path):
        _generate_gemini_tts("Hello.", tmp_path, "en")
        assert captured["headers"]["x-goog-api-key"] == "test-key"
        assert "test-key" not in captured["url"]

    def test_default_voice(self, captured, tmp_path):
        _generate_gemini_tts("Hello.", tmp_path, "en")
        voice = captured["body"]["generationConfig"]["speechConfig"]["voiceConfig"]
        assert voice["prebuiltVoiceConfig"]["voiceName"] == GEMINI_VOICE_DEFAULT

    def test_voice_override(self, captured, tmp_path):
        _generate_gemini_tts("Hello.", tmp_path, "en", voice_id="Sulafat")
        voice = captured["body"]["generationConfig"]["speechConfig"]["voiceConfig"]
        assert voice["prebuiltVoiceConfig"]["voiceName"] == "Sulafat"

    def test_style_prompt_is_prepended_to_the_text(self, captured, tmp_path):
        _generate_gemini_tts(
            "The docks were quiet.", tmp_path, "en",
            style_prompt="Read this as a restrained documentary narrator",
        )
        text = captured["body"]["contents"][0]["parts"][0]["text"]
        assert text == (
            "Read this as a restrained documentary narrator: The docks were quiet."
        )

    def test_style_prompt_trailing_colon_is_not_doubled(self, captured, tmp_path):
        _generate_gemini_tts("Text.", tmp_path, "en", style_prompt="Read slowly:")
        assert captured["body"]["contents"][0]["parts"][0]["text"] == "Read slowly: Text."

    def test_without_a_style_prompt_only_the_script_is_sent(self, captured, tmp_path):
        _generate_gemini_tts("Just this.", tmp_path, "en")
        assert captured["body"]["contents"][0]["parts"][0]["text"] == "Just this."

    def test_pcm_is_converted_with_the_declared_sample_rate(self, monkeypatch, tmp_path):
        calls = {}
        monkeypatch.setattr(tts, "get_gemini_key", lambda: "k")
        monkeypatch.setattr(
            tts.requests, "post",
            lambda *a, **k: FakeResponse(
                payload=audio_payload(b"\x00\x01" * 10, mime="audio/L16;rate=16000")
            ),
        )

        monkeypatch.setattr(tts, "run_cmd", stub_encode(calls))
        _generate_gemini_tts("Hi.", tmp_path, "en")

        assert "16000" in calls["cmd"]
        assert "s16le" in calls["cmd"]

    def test_intermediate_pcm_is_cleaned_up(self, captured, tmp_path):
        _generate_gemini_tts("Hello.", tmp_path, "en")
        assert not (tmp_path / "voiceover_en.pcm").exists()

    def test_missing_key_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, "get_gemini_key", lambda: "")
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not set"):
            _generate_gemini_tts("Hello.", tmp_path, "en")

    def test_403_includes_the_ai_studio_hint(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, "get_gemini_key", lambda: "k")
        monkeypatch.setattr(
            tts.requests, "post",
            lambda *a, **k: FakeResponse(403, {"error": {"message": "denied"}}),
        )
        with pytest.raises(RuntimeError, match="AI Studio"):
            _generate_gemini_tts("Hello.", tmp_path, "en")

    def test_response_without_audio_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, "get_gemini_key", lambda: "k")
        monkeypatch.setattr(
            tts.requests, "post",
            lambda *a, **k: FakeResponse(200, {"candidates": [{"content": {"parts": []}}]}),
        )
        with pytest.raises(RuntimeError, match="No audio"):
            _generate_gemini_tts("Hello.", tmp_path, "en")


class TestPcmRate:
    @pytest.mark.parametrize(
        "mime,expected",
        [
            ("audio/L16;codec=pcm;rate=24000", 24000),
            ("audio/L16;rate=16000", 16000),
            ("audio/L16;codec=pcm", 24000),
            ("", 24000),
            ("audio/L16;rate=notanumber", 24000),
        ],
    )
    def test_parses_rate(self, mime, expected):
        assert _pcm_rate(mime) == expected


class TestProviderRouting:
    def test_explicit_gemini_is_honoured(self):
        assert get_tts_provider("gemini") == "gemini"

    def test_gemini_is_not_auto_selected(self, monkeypatch):
        # A Gemini key is already needed for b-roll; auto-selecting it here
        # would silently move existing Shorts users onto paid narration.
        monkeypatch.delenv("TTS_PROVIDER", raising=False)
        monkeypatch.setattr(tts, "get_gemini_key", lambda: "present")
        monkeypatch.setattr("verticals.config.load_config", lambda: {})
        assert get_tts_provider(None) != "gemini"

    def test_generate_voiceover_routes_to_gemini(self, captured, tmp_path):
        out = generate_voiceover(
            "Hello.", tmp_path, "en", provider="gemini",
            voice_config={"voice_id": "Charon", "style_prompt": "Read plainly"},
        )
        assert out.exists()
        assert captured["body"]["contents"][0]["parts"][0]["text"].startswith("Read plainly:")

    def test_gemini_failure_falls_back_to_edge(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, "get_gemini_key", lambda: "k")
        monkeypatch.setattr(
            tts.requests, "post", lambda *a, **k: FakeResponse(500, text="boom")
        )
        fallback = tmp_path / "voiceover_en.mp3"

        def fake_edge(script, out_dir, lang, voice_override=""):
            fallback.write_bytes(b"edge")
            return fallback

        monkeypatch.setattr(tts, "_generate_edge_tts", fake_edge)
        assert generate_voiceover("Hi.", tmp_path, "en", provider="gemini") == fallback
