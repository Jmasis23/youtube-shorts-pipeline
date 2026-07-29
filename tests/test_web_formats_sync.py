"""The generated web module must stay in sync with the format YAML.

The CLI reads formats/*.yaml directly; the Next.js planner reads the generated
web/lib/formats.ts. One source of truth only works if the generated file is
regenerated whenever the YAML changes, so this test fails loudly when it is not.

    python3 scripts/gen_web_formats.py
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "gen_web_formats.py"
GENERATED = ROOT / "web" / "lib" / "formats.ts"


def _load_generator():
    spec = importlib.util.spec_from_file_location("gen_web_formats", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_generated() -> list[dict]:
    """Pull the JSON payload back out of the generated TypeScript module."""
    text = GENERATED.read_text(encoding="utf-8")
    marker = "export const FORMATS: FormatProfile[] = "
    start = text.index(marker) + len(marker)
    end = text.index("];", start) + 1
    return json.loads(text[start:end])


@pytest.mark.skipif(not GENERATED.exists(), reason="web app not present")
class TestGeneratedFormats:
    def test_is_up_to_date(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def test_covers_every_format(self):
        from longform.formats import list_formats

        generated = {f["name"] for f in _parse_generated()}
        assert generated == set(list_formats())

    def test_carries_the_fields_the_planner_prompts_need(self):
        for profile in _parse_generated():
            assert profile["displayName"], profile["name"]
            assert profile["tone"], profile["name"]
            assert profile["narrationStyle"], profile["name"]
            assert profile["targetMinutes"] > 0
            assert profile["chapters"] > 0
            assert profile["sceneSeconds"] > 0
            assert profile["hooks"], profile["name"]
            assert profile["retentionRules"], profile["name"]

    def test_faceless_constraint_survives_generation(self):
        for profile in _parse_generated():
            avoid = " ".join(profile["subjectsAvoid"]).lower()
            assert "face" in avoid, profile["name"]

    def test_descriptions_are_free_of_em_dashes(self):
        # Descriptions are rendered as page copy, where em-dashes are a
        # house-style violation. The prompt-only fields may still use them.
        offenders = [
            p["name"]
            for p in _parse_generated()
            if "—" in p["description"] or "–" in p["description"]
        ]
        assert offenders == []

    def test_block_scalars_are_collapsed_to_single_lines(self):
        # YAML folded scalars keep trailing newlines; those would render as
        # stray whitespace in JSX.
        for profile in _parse_generated():
            for field in ("description", "tone", "narrationStyle", "promptSuffix"):
                value = profile[field]
                assert "\n" not in value, f"{profile['name']}.{field}"
                assert value == value.strip(), f"{profile['name']}.{field}"


class TestGeneratorItself:
    def test_clean_collapses_whitespace(self):
        gen = _load_generator()
        assert gen._clean("  a\n  b  \n") == "a b"

    def test_clean_handles_none(self):
        gen = _load_generator()
        assert gen._clean(None) == ""

    def test_clean_list_drops_empties(self):
        gen = _load_generator()
        assert gen._clean_list(["a", "", None, " b "]) == ["a", "b"]

    def test_render_is_deterministic(self):
        gen = _load_generator()
        assert gen.render() == gen.render()
