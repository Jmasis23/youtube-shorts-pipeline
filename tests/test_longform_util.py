"""Tests for longform.util and longform.config — the pure helpers."""

import pytest

from longform.config import (
    chapter_word_budgets,
    minutes_for_words,
    scene_count_for,
    words_for_minutes,
)
from longform.util import (
    chunk_text,
    escape_concat_path,
    format_timestamp,
    parse_json_response,
    split_sentences,
    truncate_words,
    word_count,
)


class TestParseJsonResponse:
    def test_plain_json(self):
        assert parse_json_response('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        raw = '```json\n{"a": 1, "b": "two"}\n```'
        assert parse_json_response(raw) == {"a": 1, "b": "two"}

    def test_fenced_without_language(self):
        assert parse_json_response('```\n{"a": 1}\n```') == {"a": 1}

    def test_wrapped_in_prose(self):
        raw = 'Here is the outline you asked for:\n{"a": 1}\nHope that helps!'
        assert parse_json_response(raw) == {"a": 1}

    def test_nested_objects_survive(self):
        raw = '{"outer": {"inner": [1, 2]}}'
        assert parse_json_response(raw)["outer"]["inner"] == [1, 2]

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON object"):
            parse_json_response("I'm afraid I can't do that.")

    def test_malformed_json_raises(self):
        with pytest.raises(ValueError, match="Malformed JSON"):
            parse_json_response('{"a": 1,,}')


class TestChunkText:
    def test_short_text_is_one_chunk(self):
        assert chunk_text("One sentence here.", 100) == ["One sentence here."]

    def test_splits_on_sentence_boundaries(self):
        text = "A" * 40 + ". " + "B" * 40 + ". " + "C" * 40 + "."
        chunks = chunk_text(text, 90)
        assert len(chunks) > 1
        assert all(len(c) <= 90 for c in chunks)

    def test_no_content_is_lost(self):
        text = " ".join(f"Sentence number {i}." for i in range(50))
        chunks = chunk_text(text, 120)
        assert " ".join(chunks) == text

    def test_oversized_sentence_is_split_not_dropped(self):
        # One sentence with no internal punctuation, far past the limit.
        text = " ".join(["word"] * 200) + "."
        chunks = chunk_text(text, 100)
        assert all(len(c) <= 100 for c in chunks)
        assert word_count(" ".join(chunks)) == 200

    def test_empty_text(self):
        assert chunk_text("", 100) == []

    def test_invalid_max_chars(self):
        with pytest.raises(ValueError):
            chunk_text("hello", 0)


class TestSplitSentences:
    def test_basic(self):
        assert split_sentences("One. Two! Three?") == ["One.", "Two!", "Three?"]

    def test_empty(self):
        assert split_sentences("") == []


class TestFormatTimestamp:
    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (0, "0:00"),
            (5, "0:05"),
            (65, "1:05"),
            (600, "10:00"),
            (3600, "1:00:00"),
            (3725, "1:02:05"),
            (-4, "0:00"),
        ],
    )
    def test_formats(self, seconds, expected):
        assert format_timestamp(seconds) == expected


class TestMisc:
    def test_escape_concat_path(self):
        assert escape_concat_path("/tmp/it's here.mp3") == "/tmp/it'\\''s here.mp3"

    def test_truncate_words_under_limit(self):
        assert truncate_words("three words here", 10) == "three words here"

    def test_truncate_words_over_limit(self):
        assert truncate_words("a b c d e", 3) == "a b c."


class TestPacing:
    def test_words_for_minutes(self):
        assert words_for_minutes(10) == 1500

    def test_round_trip(self):
        assert minutes_for_words(words_for_minutes(12)) == pytest.approx(12)

    def test_scene_count_scales_with_duration(self):
        assert scene_count_for(90, 9) == 10
        assert scene_count_for(900, 9) == 100

    def test_scene_count_never_zero(self):
        assert scene_count_for(1.0, 9) == 1

    def test_scene_seconds_are_clamped(self):
        # An absurd scene length is clamped rather than producing one scene.
        assert scene_count_for(600, 1000) == scene_count_for(600, 20)


class TestChapterWordBudgets:
    def test_budgets_sum_to_total(self):
        b = chapter_word_budgets(10, 5)
        assert b["intro"] + sum(b["chapters"]) + b["outro"] == b["total"]

    def test_chapter_count_respected(self):
        assert len(chapter_word_budgets(15, 7)["chapters"]) == 7

    def test_longer_runtime_means_more_words(self):
        assert chapter_word_budgets(20, 5)["total"] > chapter_word_budgets(10, 5)["total"]

    def test_intro_and_outro_are_short(self):
        b = chapter_word_budgets(15, 6)
        assert b["intro"] < min(b["chapters"])
        assert b["outro"] < min(b["chapters"])

    def test_single_chapter(self):
        b = chapter_word_budgets(5, 1)
        assert len(b["chapters"]) == 1
        assert b["chapters"][0] > 0

    def test_total_is_close_to_target_runtime(self):
        b = chapter_word_budgets(12, 6)
        assert 12 * 150 * 0.95 <= b["total"] <= 12 * 150 * 1.05
