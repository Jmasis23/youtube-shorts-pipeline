#!/usr/bin/env python3
"""Generate web/lib/formats.ts from the format profiles in formats/.

The web planner needs the same format intelligence the CLI uses. Rather than
duplicating it in TypeScript (where it would drift on the first edit), this
emits a generated module from the YAML and a test asserts the two stay in sync.

Run after editing anything under formats/:

    python3 scripts/gen_web_formats.py
"""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FORMATS_DIR = ROOT / "formats"
OUT_PATH = ROOT / "web" / "lib" / "formats.ts"

HEADER = """// GENERATED FILE. Do not edit by hand.
// Source: formats/*.yaml
// Regenerate: python3 scripts/gen_web_formats.py
//
// The CLI reads the YAML directly; the web planner reads this module. Keeping
// one source of truth is what stops the two halves drifting apart.

export interface FormatHook {
  template: string;
  when?: string;
}

export interface FormatProfile {
  name: string;
  displayName: string;
  description: string;
  targetMinutes: number;
  chapters: number;
  sceneSeconds: number;
  tone: string;
  narrationStyle: string;
  perspective: string;
  arc: Record<string, string>;
  openLoop: string;
  retentionRules: string[];
  hooks: FormatHook[];
  cta: string;
  forbiddenPhrases: string[];
  voiceName: string;
  voiceStyle: string;
  categoryId: string;
  titleStyle: string;
  visualStyle: string;
  visualMood: string;
  promptSuffix: string;
  subjectsPrefer: string[];
  subjectsAvoid: string[];
  burnCaptions: boolean;
}

"""

FOOTER = """
export const FORMAT_NAMES = FORMATS.map((f) => f.name);

export function getFormat(name: string): FormatProfile {
  return FORMATS.find((f) => f.name === name) ?? FORMATS[0];
}
"""


def _clean(value) -> str:
    """Collapse YAML block scalars into single-line strings."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def _clean_list(value) -> list[str]:
    if not value:
        return []
    return [_clean(v) for v in value if _clean(v)]


def build_profile(path: Path) -> dict:
    profile = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    script = profile.get("script", {}) or {}
    visuals = profile.get("visuals", {}) or {}
    voice = profile.get("voice", {}) or {}
    captions = profile.get("captions", {}) or {}
    metadata = profile.get("metadata", {}) or {}
    subjects = visuals.get("subjects", {}) or {}
    retention = script.get("retention", {}) or {}

    hooks = []
    for hook in script.get("hooks", []) or []:
        if isinstance(hook, dict) and hook.get("template"):
            entry = {"template": _clean(hook["template"])}
            if hook.get("when"):
                entry["when"] = _clean(hook["when"])
            hooks.append(entry)

    gemini_voices = (voice.get("suggested_voices", {}) or {}).get("gemini", {}) or {}

    return {
        "name": profile.get("name", path.stem),
        "displayName": profile.get("display_name", path.stem.title()),
        "description": _clean(profile.get("description")),
        "targetMinutes": int(profile.get("target_minutes", 10)),
        "chapters": int(profile.get("chapters", 5)),
        "sceneSeconds": float(visuals.get("scene_seconds", 9)),
        "tone": _clean(script.get("tone")),
        "narrationStyle": _clean(script.get("narration_style")),
        "perspective": _clean(script.get("perspective")),
        "arc": {k: _clean(v) for k, v in (script.get("arc", {}) or {}).items()},
        "openLoop": _clean(retention.get("open_loop")),
        "retentionRules": _clean_list(retention.get("rules")),
        "hooks": hooks,
        "cta": _clean(script.get("cta")),
        "forbiddenPhrases": _clean_list(script.get("forbidden_phrases")),
        "voiceName": _clean(gemini_voices.get("en")),
        "voiceStyle": _clean(voice.get("style_prompt")),
        "categoryId": str(metadata.get("category_id", "27")),
        "titleStyle": _clean(metadata.get("title_style")),
        "visualStyle": _clean(visuals.get("style")),
        "visualMood": _clean(visuals.get("mood")),
        "promptSuffix": _clean(visuals.get("prompt_suffix")),
        "subjectsPrefer": _clean_list(subjects.get("prefer")),
        "subjectsAvoid": _clean_list(subjects.get("avoid")),
        "burnCaptions": bool(captions.get("burn_in", False)),
    }


def render() -> str:
    profiles = [build_profile(p) for p in sorted(FORMATS_DIR.glob("*.yaml"))]
    body = json.dumps(profiles, indent=2, ensure_ascii=False)
    return f"{HEADER}export const FORMATS: FormatProfile[] = {body};\n{FOOTER}"


def main() -> int:
    if not FORMATS_DIR.exists():
        print(f"No formats directory at {FORMATS_DIR}", file=sys.stderr)
        return 1

    generated = render()
    check_only = "--check" in sys.argv

    if check_only:
        if not OUT_PATH.exists():
            print(f"{OUT_PATH} is missing. Run: python3 scripts/gen_web_formats.py")
            return 1
        if OUT_PATH.read_text(encoding="utf-8") != generated:
            print(
                f"{OUT_PATH} is stale. Run: python3 scripts/gen_web_formats.py"
            )
            return 1
        print(f"{OUT_PATH.relative_to(ROOT)} is up to date.")
        return 0

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(generated, encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)} ({len(generated.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
