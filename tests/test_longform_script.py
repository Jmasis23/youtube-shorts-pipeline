"""Tests for the two-pass writing path — outline planning and section writing."""

import json

import pytest

from longform.outline import _normalise, generate_outline, outline_summary
from longform.script import _section_plan, write_script


@pytest.fixture
def outline():
    """A normalised outline as generate_outline would return it."""
    return {
        "working_title": "How Container Shipping Actually Works",
        "thesis": "Container shipping is a standardisation story, not a boats story.",
        "audience_promise": "You will be able to explain why a box changed trade.",
        "cold_open_hook": "A steel box changed the world more than the ship carrying it.",
        "open_loop": {"setup": "why the box, not the ship", "payoff_chapter": 2},
        "intro": {"title": "Intro", "job": "Open the loop", "beats": ["hook"], "word_budget": 120},
        "chapters": [
            {"title": "Before The Box", "job": "Establish the old world",
             "beats": ["break-bulk", "dock labour"], "ends_on": "cost problem",
             "word_budget": 400},
            {"title": "The Standard", "job": "Pay off the loop",
             "beats": ["ISO sizes"], "ends_on": "adoption problem", "word_budget": 400},
            {"title": "The Ports", "job": "Show the second-order effects",
             "beats": ["cranes"], "ends_on": "", "word_budget": 400},
        ],
        "outro": {"title": "Outro", "job": "Land the payoff", "beats": ["recap"],
                  "word_budget": 100},
        "payoff": "Standardisation, not scale, is what compounded.",
        "cta": "Watch the one on the ports next.",
        "thumbnail_prompt": "A single container on an empty quay at dawn",
        "keywords": ["shipping", "logistics"],
        "topic": "How container shipping works",
        "format": "explainer",
        "niche": "general",
        "research": "Malcom McLean, 1956, Ideal X.",
        "word_budgets": {"intro": 120, "chapters": [400, 400, 400], "outro": 100,
                         "total": 1420},
    }


class TestNormalise:
    def test_pads_missing_chapters(self):
        # The model returned two chapters when five were planned.
        budgets = {"intro": 100, "chapters": [300] * 5, "outro": 80, "total": 1680}
        data = {"chapters": [{"title": "One"}, {"title": "Two"}]}
        result = _normalise(data, budgets, 5)
        assert len(result["chapters"]) == 5
        assert all(c["word_budget"] == 300 for c in result["chapters"])

    def test_trims_extra_chapters(self):
        budgets = {"intro": 100, "chapters": [300] * 2, "outro": 80, "total": 780}
        data = {"chapters": [{"title": f"C{i}"} for i in range(6)]}
        assert len(_normalise(data, budgets, 2)["chapters"]) == 2

    def test_coerces_string_beats_to_list(self):
        budgets = {"intro": 100, "chapters": [300], "outro": 80, "total": 480}
        data = {"chapters": [{"title": "One", "beats": "a single beat"}]}
        assert _normalise(data, budgets, 1)["chapters"][0]["beats"] == ["a single beat"]

    def test_clamps_out_of_range_payoff_chapter(self):
        budgets = {"intro": 100, "chapters": [300] * 3, "outro": 80, "total": 1080}
        data = {"chapters": [{"title": "a"}, {"title": "b"}, {"title": "c"}],
                "open_loop": {"setup": "x", "payoff_chapter": 99}}
        assert _normalise(data, budgets, 3)["open_loop"]["payoff_chapter"] == 3

    def test_non_numeric_payoff_chapter(self):
        budgets = {"intro": 100, "chapters": [300], "outro": 80, "total": 480}
        data = {"chapters": [{"title": "a"}], "open_loop": {"payoff_chapter": "two"}}
        assert _normalise(data, budgets, 1)["open_loop"]["payoff_chapter"] == 0

    def test_missing_intro_and_outro_get_defaults(self):
        budgets = {"intro": 100, "chapters": [300], "outro": 80, "total": 480}
        result = _normalise({"chapters": [{"title": "a"}]}, budgets, 1)
        assert result["intro"]["title"] == "Intro"
        assert result["outro"]["word_budget"] == 80


class TestGenerateOutline:
    def test_builds_outline_from_llm_response(self, monkeypatch):
        response = json.dumps({
            "working_title": "T",
            "thesis": "Th",
            "cold_open_hook": "Hook.",
            "open_loop": {"setup": "s", "payoff_chapter": 1},
            "intro": {"title": "Intro", "job": "j", "beats": ["b"]},
            "chapters": [{"title": "One", "job": "j", "beats": ["b"], "ends_on": "e"}],
            "outro": {"title": "Outro", "job": "j", "beats": ["b"]},
            "payoff": "p", "cta": "c", "thumbnail_prompt": "tp",
            "keywords": ["k"],
        })
        monkeypatch.setattr("longform.outline.call_llm", lambda *a, **k: response)
        monkeypatch.setattr("longform.outline.research_topic", lambda t: "RESEARCH")

        result = generate_outline("Topic", fmt="explainer", chapter_count=1, target_minutes=5)

        assert result["working_title"] == "T"
        assert result["target_minutes"] == 5
        assert result["research"] == "RESEARCH"
        assert result["chapters"][0]["word_budget"] > 0

    def test_research_can_be_disabled(self, monkeypatch):
        called = []
        monkeypatch.setattr(
            "longform.outline.research_topic",
            lambda t: called.append(t) or "SHOULD NOT HAPPEN",
        )
        monkeypatch.setattr(
            "longform.outline.call_llm",
            lambda *a, **k: json.dumps({"chapters": [{"title": "One"}]}),
        )
        result = generate_outline("Topic", chapter_count=1, research=False)
        assert called == []
        assert "Research disabled" in result["research"]

    def test_summary_renders(self, outline):
        summary = outline_summary(outline)
        assert "Before The Box" in summary
        assert "open loop payoff" in summary


class TestSectionPlan:
    def test_plan_covers_intro_chapters_and_outro(self, outline):
        plan = _section_plan(outline)
        assert [s["key"] for s in plan] == ["intro", "chapter", "chapter", "chapter", "outro"]

    def test_payoff_chapter_is_marked(self, outline):
        plan = _section_plan(outline)
        assert [s["is_payoff"] for s in plan] == [False, False, True, False, False]


class TestWriteScript:
    def _fake_llm(self, calls, words=400):
        def _call(prompt, provider=None, max_tokens=1500):
            calls.append(prompt)
            return json.dumps({
                "narration": " ".join(["word"] * words),
                "visual_prompts": ["a shot", "another shot"],
                "summary": f"summary {len(calls)}",
            })
        return _call

    def test_writes_one_section_per_plan_entry(self, outline, monkeypatch):
        calls = []
        monkeypatch.setattr("longform.script.call_llm", self._fake_llm(calls))
        sections = write_script(outline)
        assert len(sections) == 5
        assert len(calls) == 5

    def test_rolling_context_grows(self, outline, monkeypatch):
        calls = []
        monkeypatch.setattr("longform.script.call_llm", self._fake_llm(calls))
        write_script(outline)

        # The first call has nothing written yet; later calls carry summaries.
        assert "nothing yet" in calls[0]
        assert "summary 1" in calls[1]
        assert "summary 1" in calls[-1] and "summary 4" in calls[-1]

    def test_payoff_chapter_prompt_says_so(self, outline, monkeypatch):
        calls = []
        monkeypatch.setattr("longform.script.call_llm", self._fake_llm(calls))
        write_script(outline)
        payoff_prompts = [c for c in calls if "PAYS OFF THE OPEN LOOP" in c]
        assert len(payoff_prompts) == 1

    def test_faceless_rules_in_every_prompt(self, outline, monkeypatch):
        calls = []
        monkeypatch.setattr("longform.script.call_llm", self._fake_llm(calls))
        write_script(outline)
        assert all("FACELESS CONSTRAINTS" in c for c in calls)

    def test_short_section_triggers_one_expansion(self, outline, monkeypatch):
        calls = []

        def _call(prompt, provider=None, max_tokens=1500):
            calls.append(prompt)
            if "too short" in prompt:
                return json.dumps({"narration": " ".join(["word"] * 400)})
            return json.dumps({
                "narration": "far too short",
                "visual_prompts": ["a shot"],
                "summary": "s",
            })

        monkeypatch.setattr("longform.script.call_llm", _call)
        sections = write_script(outline)

        # Every section was short, so every one got an expansion pass.
        assert sum("too short" in c for c in calls) == 5
        assert all(s["word_count"] == 400 for s in sections)

    def test_empty_narration_raises(self, outline, monkeypatch):
        monkeypatch.setattr(
            "longform.script.call_llm",
            lambda *a, **k: json.dumps({"narration": "", "visual_prompts": []}),
        )
        with pytest.raises(RuntimeError, match="no narration"):
            write_script(outline)

    def test_missing_visual_prompts_get_a_fallback(self, outline, monkeypatch):
        monkeypatch.setattr(
            "longform.script.call_llm",
            lambda *a, **k: json.dumps({
                "narration": " ".join(["word"] * 400),
                "visual_prompts": [],
                "summary": "s",
            }),
        )
        sections = write_script(outline)
        assert all(s["visual_prompts"] for s in sections)

    def test_progress_callback_fires(self, outline, monkeypatch):
        monkeypatch.setattr("longform.script.call_llm", self._fake_llm([]))
        seen = []
        write_script(outline, on_progress=lambda i, total, title: seen.append((i, total)))
        assert seen == [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)]
