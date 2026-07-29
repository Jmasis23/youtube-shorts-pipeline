"""Tests for scene planning, metadata assembly, and project state."""

import json

import pytest

from longform.metadata import _fit_tags, build_description, generate_metadata
from longform.project import Project, list_projects
from longform.visuals import _compose_prompt, plan_scenes


@pytest.fixture
def rendered_sections():
    return [
        {"index": 0, "title": "Intro", "duration": 60.0, "start": 0.0, "end": 60.0,
         "gap_after": 0.7},
        {"index": 1, "title": "Chapter One", "duration": 180.0, "start": 60.7,
         "end": 240.7, "gap_after": 0.7},
        {"index": 2, "title": "Outro", "duration": 45.0, "start": 241.4, "end": 286.4,
         "gap_after": 0.0},
    ]


@pytest.fixture
def sections():
    return [
        {"key": "intro", "title": "Intro", "narration": "x",
         "visual_prompts": ["intro shot a", "intro shot b"]},
        {"key": "chapter", "title": "Chapter One", "narration": "x",
         "visual_prompts": ["ch1 shot a", "ch1 shot b", "ch1 shot c"]},
        {"key": "outro", "title": "Outro", "narration": "x",
         "visual_prompts": ["outro shot"]},
    ]


class TestPlanScenes:
    def test_scene_count_tracks_duration(self, rendered_sections, sections):
        scenes = plan_scenes(rendered_sections, sections, scene_seconds=10)
        # 60s -> 6, 180s -> 18, 45s -> 4 (rounded)
        per_section = [
            sum(1 for s in scenes if s["section_index"] == i) for i in range(3)
        ]
        assert per_section == [6, 18, 4]

    def test_scene_durations_cover_the_whole_timeline(self, rendered_sections, sections):
        scenes = plan_scenes(rendered_sections, sections, scene_seconds=10)
        total_audio = sum(r["duration"] + r["gap_after"] for r in rendered_sections)
        assert sum(s["duration"] for s in scenes) == pytest.approx(total_audio, abs=0.05)

    def test_gaps_are_absorbed_not_dropped(self, rendered_sections, sections):
        # Without absorbing the inter-section silence, visuals drift early.
        scenes = plan_scenes(rendered_sections, sections, scene_seconds=10)
        last_intro_scene = [s for s in scenes if s["section_index"] == 0][-1]
        other_intro_scene = [s for s in scenes if s["section_index"] == 0][0]
        assert last_intro_scene["duration"] > other_intro_scene["duration"]

    def test_starts_are_monotonic(self, rendered_sections, sections):
        scenes = plan_scenes(rendered_sections, sections, scene_seconds=10)
        starts = [s["start"] for s in scenes]
        assert starts == sorted(starts)

    def test_prompts_cycle_when_a_section_outruns_them(self, rendered_sections, sections):
        scenes = plan_scenes(rendered_sections, sections, scene_seconds=10)
        outro_scenes = [s for s in scenes if s["section_index"] == 2]
        # One prompt, four scenes — reused rather than leaving blanks.
        assert len(outro_scenes) == 4
        assert all("outro shot" in s["prompt"] for s in outro_scenes)

    def test_reused_prompts_get_different_camera_moves(self, rendered_sections, sections):
        scenes = plan_scenes(
            rendered_sections, sections, scene_seconds=10,
            motion=["zoom_in", "pan_right", "zoom_out", "pan_left"],
        )
        outro_effects = [s["effect"] for s in scenes if s["section_index"] == 2]
        assert len(set(outro_effects)) == 4

    def test_prompt_suffix_is_applied(self, rendered_sections, sections):
        scenes = plan_scenes(
            rendered_sections, sections, scene_seconds=10,
            prompt_suffix="film grain, no text",
        )
        assert all(s["prompt"].endswith("film grain, no text") for s in scenes)

    def test_section_without_prompts_gets_a_fallback(self, rendered_sections):
        bare = [{"key": "intro", "title": "Intro", "visual_prompts": []}] * 3
        scenes = plan_scenes(rendered_sections, bare, scene_seconds=10)
        assert all(s["prompt"] for s in scenes)

    def test_compose_prompt_without_suffix(self):
        assert _compose_prompt("a shot.", "") == "a shot"


class TestMetadata:
    def test_fit_tags_dedupes_and_lowercases(self):
        assert _fit_tags(["Shipping", "shipping", "#Ports"]) == ["shipping", "ports"]

    def test_fit_tags_respects_the_character_budget(self):
        tags = _fit_tags([f"a-fairly-long-tag-number-{i}" for i in range(60)])
        assert sum(len(t) + 1 for t in tags) <= 480

    def test_description_puts_chapters_above_the_body(self):
        markers = [
            {"timestamp": "0:00", "title": "Intro"},
            {"timestamp": "1:30", "title": "One"},
        ]
        description = build_description(
            {"description_intro": "INTRO TEXT", "description_body": "BODY TEXT"},
            markers,
        )
        assert description.index("INTRO TEXT") < description.index("0:00 Intro")
        assert description.index("0:00 Intro") < description.index("BODY TEXT")

    def test_description_includes_extra_links(self):
        description = build_description(
            {"description_intro": "i", "description_body": "b"}, [], extra_links="LINKS"
        )
        assert description.endswith("LINKS")

    def test_description_is_truncated_to_the_youtube_limit(self):
        description = build_description(
            {"description_intro": "i", "description_body": "x" * 6000}, []
        )
        assert len(description) <= 5000
        assert description.endswith("...")

    def test_generate_metadata_shapes_the_response(self, monkeypatch):
        monkeypatch.setattr(
            "longform.metadata.call_llm",
            lambda *a, **k: json.dumps({
                "titles": ["A" * 150, "Second", "Third"],
                "description_intro": "intro",
                "description_body": "body",
                "tags": ["One", "TWO"],
                "pinned_comment": "question?",
                "thumbnail_prompt": "tp",
            }),
        )
        markers = [{"timestamp": "0:00", "title": "Intro", "end": 600}]
        meta = generate_metadata({"topic": "t"}, markers, fmt="explainer")

        assert len(meta["youtube_title"]) == 100  # trimmed to YouTube's limit
        assert meta["youtube_tags"] == "one,two"
        assert meta["youtube_category_id"] == "27"
        assert len(meta["title_options"]) == 3

    def test_generate_metadata_falls_back_to_outline_keywords(self, monkeypatch):
        monkeypatch.setattr(
            "longform.metadata.call_llm",
            lambda *a, **k: json.dumps({"titles": ["T"], "tags": []}),
        )
        meta = generate_metadata(
            {"topic": "t", "keywords": ["fallback"], "thumbnail_prompt": "from outline"},
            [{"timestamp": "0:00", "title": "I", "end": 60}],
        )
        assert meta["youtube_tags"] == "fallback"
        assert meta["thumbnail_prompt"] == "from outline"


class TestProject:
    @pytest.fixture(autouse=True)
    def _isolate(self, tmp_path, monkeypatch):
        monkeypatch.setattr("longform.project.PROJECTS_DIR", tmp_path / "projects")
        monkeypatch.setattr("longform.project.ensure_dirs", lambda: None)
        (tmp_path / "projects").mkdir()

    def test_create_and_save(self):
        project = Project.create("Topic", "documentary", "tech")
        path = project.save()
        assert path.exists()
        assert json.loads(path.read_text())["topic"] == "Topic"

    def test_topic_mirrors_to_news_for_the_shared_uploader(self):
        # verticals.upload reads draft["news"]; long-form projects must satisfy it.
        assert Project.create("Topic", "explainer", "general").data["news"] == "Topic"

    def test_load_round_trip(self):
        project = Project.create("Topic", "explainer", "general")
        project.set("word_count", 1234)
        path = project.save()

        loaded = Project.load(path)
        assert loaded.get("word_count") == 1234
        assert loaded.project_id == project.project_id

    def test_load_by_bare_id(self, tmp_path):
        project = Project.create("Topic", "explainer", "general")
        project.save()
        assert Project.load(project.project_id).get("topic") == "Topic"

    def test_load_missing_raises(self):
        with pytest.raises(FileNotFoundError):
            Project.load("9999999999")

    def test_stage_tracking_survives_a_round_trip(self):
        project = Project.create("Topic", "explainer", "general")
        project.complete("narration", {"duration": 612.5})
        path = project.save()

        loaded = Project.load(path)
        assert loaded.is_done("narration")
        assert loaded.artifact("narration", "duration") == 612.5
        assert not loaded.is_done("assemble")

    def test_summary_lists_every_stage(self):
        project = Project.create("Topic", "explainer", "general")
        project.complete("outline")
        summary = project.summary()
        assert "[+] outline" in summary
        assert "[ ] upload" in summary

    def test_project_ids_do_not_collide_within_a_second(self, monkeypatch):
        # Both projects get the same timestamp; the second must not overwrite.
        monkeypatch.setattr("longform.project.time.time", lambda: 1700000000.0)
        first = Project.create("First", "explainer", "general")
        first.save()
        second = Project.create("Second", "explainer", "general")
        second.save()

        assert first.project_id != second.project_id
        assert Project.load(first.path).get("topic") == "First"
        assert Project.load(second.path).get("topic") == "Second"

    def test_list_projects(self):
        Project.create("First", "explainer", "general").save()
        Project.create("Second", "story", "general").save()
        listed = list_projects()
        assert len(listed) == 2
        assert {p["topic"] for p in listed} == {"First", "Second"}

    def test_list_projects_skips_corrupt_files(self, tmp_path):
        Project.create("Good", "explainer", "general").save()
        (tmp_path / "projects" / "broken.json").write_text("{not json")
        assert [p["topic"] for p in list_projects()] == ["Good"]
