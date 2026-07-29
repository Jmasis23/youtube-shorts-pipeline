"""Tests for chapter markers and subtitle cue grouping."""

import pytest

from longform.chapters import (
    build_markers,
    chapters_block,
    total_runtime,
    validate_markers,
)
from longform.subtitles import group_into_cues, write_srt, _srt_time


@pytest.fixture
def rendered_sections():
    """Measured section timings as narration.synthesize_sections returns them."""
    return [
        {"index": 0, "title": "Intro", "duration": 48.0, "start": 0.0, "end": 48.0},
        {"index": 1, "title": "The Setup", "duration": 180.0, "start": 48.7, "end": 228.7},
        {"index": 2, "title": "The Turn", "duration": 210.0, "start": 229.4, "end": 439.4},
        {"index": 3, "title": "Outro", "duration": 60.0, "start": 440.1, "end": 500.1},
    ]


class TestBuildMarkers:
    def test_one_marker_per_section(self, rendered_sections):
        assert len(build_markers(rendered_sections)) == 4

    def test_first_marker_is_forced_to_zero(self):
        # Even if the intro's measured start drifted, chapters need 0:00.
        sections = [
            {"index": 0, "title": "Intro", "duration": 30.0, "start": 1.4, "end": 31.4},
            {"index": 1, "title": "One", "duration": 200.0, "start": 32.1, "end": 232.1},
            {"index": 2, "title": "Two", "duration": 200.0, "start": 232.8, "end": 432.8},
        ]
        assert build_markers(sections)[0]["start"] == 0.0

    def test_timestamps_are_formatted(self, rendered_sections):
        markers = build_markers(rendered_sections)
        assert markers[0]["timestamp"] == "0:00"
        assert markers[1]["timestamp"] == "0:48"
        assert markers[2]["timestamp"] == "3:49"

    def test_total_runtime(self, rendered_sections):
        assert total_runtime(build_markers(rendered_sections)) == pytest.approx(500.1)


class TestValidateMarkers:
    def test_valid_markers_have_no_problems(self, rendered_sections):
        assert validate_markers(build_markers(rendered_sections)) == []

    def test_too_few_chapters_is_flagged(self):
        markers = build_markers([
            {"index": 0, "title": "A", "duration": 100.0, "start": 0.0, "end": 100.0},
            {"index": 1, "title": "B", "duration": 100.0, "start": 100.0, "end": 200.0},
        ])
        problems = validate_markers(markers)
        assert any("at least 3" in p for p in problems)

    def test_short_chapter_is_flagged(self):
        markers = build_markers([
            {"index": 0, "title": "A", "duration": 100.0, "start": 0.0, "end": 100.0},
            {"index": 1, "title": "Blink", "duration": 4.0, "start": 100.0, "end": 104.0},
            {"index": 2, "title": "C", "duration": 100.0, "start": 104.0, "end": 204.0},
        ])
        problems = validate_markers(markers)
        assert any("Blink" in p and "10s minimum" in p for p in problems)

    def test_out_of_order_is_flagged(self):
        markers = [
            {"index": 0, "title": "A", "start": 0.0, "end": 60.0, "duration": 60.0, "timestamp": "0:00"},
            {"index": 1, "title": "B", "start": 200.0, "end": 260.0, "duration": 60.0, "timestamp": "3:20"},
            {"index": 2, "title": "C", "start": 100.0, "end": 160.0, "duration": 60.0, "timestamp": "1:40"},
        ]
        assert any("ascending" in p for p in validate_markers(markers))


class TestChaptersBlock:
    def test_block_format(self, rendered_sections):
        block = chapters_block(build_markers(rendered_sections))
        lines = block.splitlines()
        assert lines[0] == "0:00 Intro"
        assert lines[1] == "0:48 The Setup"
        assert len(lines) == 4

    def test_starts_at_zero(self, rendered_sections):
        # YouTube ignores the whole block unless the first line is 0:00.
        assert chapters_block(build_markers(rendered_sections)).startswith("0:00 ")


class TestGroupIntoCues:
    def test_breaks_on_word_cap(self, sample_words):
        cues = group_into_cues(sample_words, words_per_line=4)
        assert all(len(c["text"].split()) <= 4 for c in cues)

    def test_breaks_on_sentence_end(self):
        words = [
            {"word": "Stop", "start": 0.0, "end": 0.4},
            {"word": "here.", "start": 0.4, "end": 0.8},
            {"word": "New", "start": 0.9, "end": 1.2},
            {"word": "cue", "start": 1.2, "end": 1.5},
        ]
        cues = group_into_cues(words, words_per_line=20)
        assert len(cues) == 2
        assert cues[0]["text"] == "Stop here."

    def test_breaks_on_pause(self):
        words = [
            {"word": "before", "start": 0.0, "end": 0.5},
            {"word": "after", "start": 3.0, "end": 3.5},
        ]
        cues = group_into_cues(words, words_per_line=20)
        assert len(cues) == 2

    def test_no_cue_outstays_the_cap(self):
        # Slow words with no punctuation would otherwise run indefinitely.
        words = [
            {"word": f"w{i}", "start": float(i) * 1.5, "end": float(i) * 1.5 + 1.4}
            for i in range(20)
        ]
        cues = group_into_cues(words, words_per_line=50)
        assert len(cues) > 1
        assert all(c["end"] - c["start"] <= 8.0 for c in cues)

    def test_covers_every_word(self, sample_words):
        cues = group_into_cues(sample_words, words_per_line=5)
        recombined = " ".join(c["text"] for c in cues).split()
        assert recombined == [w["word"] for w in sample_words]

    def test_empty_input(self):
        assert group_into_cues([]) == []


class TestSrt:
    def test_srt_time_format(self):
        assert _srt_time(0) == "00:00:00,000"
        assert _srt_time(3725.5) == "01:02:05,500"

    def test_srt_time_rounding_carry(self):
        # .9999 must not render as ,1000
        assert _srt_time(1.9999) == "00:00:02,000"

    def test_write_srt(self, tmp_path, sample_words):
        cues = group_into_cues(sample_words, words_per_line=4)
        out = write_srt(cues, tmp_path / "s.srt")
        content = out.read_text()
        assert content.startswith("1\n")
        assert "-->" in content
        assert content.count("-->") == len(cues)
