"""Project file — the resumable unit of work for a long-form video.

A long-form render is long enough that resumability is not a nicety. Writing
the script costs a dozen LLM calls, the images cost real money, and the final
encode runs for minutes. Every stage records what it produced in the project
JSON, so a failure at minute nine picks up from stage eight.
"""

import json
import time
from pathlib import Path

from verticals.state import PipelineState

from .config import PROJECTS_DIR, ensure_dirs

# Ordered stages of a long-form build.
STAGES = [
    "outline",
    "script",
    "narration",
    "scenes",
    "images",
    "clips",
    "subtitles",
    "assemble",
    "metadata",
    "thumbnail",
    "upload",
]


def _next_project_id() -> str:
    """A project id that is unique on disk.

    The base is a unix timestamp, but two projects started in the same second
    would otherwise share a file and the second would silently overwrite the
    first — so a collision gets a suffix.
    """
    base = str(int(time.time()))
    candidate = base
    suffix = 1
    while (PROJECTS_DIR / f"{candidate}.json").exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


class Project:
    """A long-form video project, backed by a JSON file on disk."""

    def __init__(self, data: dict, path: Path | None = None):
        self.data = data
        self.path = path
        self.state = PipelineState(self.data)

    # ── lifecycle ────────────────────────────────────

    @classmethod
    def create(cls, topic: str, fmt: str, niche: str) -> "Project":
        ensure_dirs()
        project_id = _next_project_id()
        data = {
            "project_id": project_id,
            "topic": topic,
            # `news` mirrors `topic` so verticals.upload, which is shared with
            # the shorts engine, can read this project as a draft.
            "news": topic,
            "format": fmt,
            "niche": niche,
            "created_at": project_id,
        }
        return cls(data, PROJECTS_DIR / f"{project_id}.json")

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        path = Path(path)
        if not path.exists():
            # Allow referring to a project by bare id.
            candidate = PROJECTS_DIR / f"{path.name}.json"
            if candidate.exists():
                path = candidate
            else:
                raise FileNotFoundError(f"No project at {path}")
        return cls(json.loads(path.read_text()), path)

    def save(self) -> Path:
        if self.path is None:
            ensure_dirs()
            self.path = PROJECTS_DIR / f"{self.data['project_id']}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))
        return self.path

    # ── convenience accessors ────────────────────────

    @property
    def project_id(self) -> str:
        return self.data["project_id"]

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value):
        self.data[key] = value

    def work_dir(self, lang: str = "en") -> Path:
        from .config import MEDIA_DIR

        d = MEDIA_DIR / f"work_{self.project_id}_{lang}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── stage tracking ───────────────────────────────

    def is_done(self, stage: str) -> bool:
        return self.state.is_done(stage)

    def complete(self, stage: str, artifacts: dict | None = None):
        self.state.complete_stage(stage, artifacts)

    def artifact(self, stage: str, key: str, default=None):
        return self.state.get_artifact(stage, key, default)

    def summary(self) -> str:
        lines = [
            f"  Project   : {self.project_id}",
            f"  Topic     : {self.get('topic', '')}",
            f"  Format    : {self.get('format', '')} / {self.get('niche', '')}",
            f"  Title     : {self.get('youtube_title') or self.get('outline', {}).get('working_title', '—')}",
            "",
            "  Stages:",
        ]
        for stage in STAGES:
            entry = self.data.get("_pipeline_state", {}).get(stage, {})
            status = entry.get("status", "pending")
            marker = {"done": "+", "failed": "!", "pending": " "}.get(status, "?")
            lines.append(f"    [{marker}] {stage}")

        if self.get("video_path"):
            lines += ["", f"  Video     : {self.get('video_path')}"]
        if self.get("youtube_url"):
            lines += [f"  Live      : {self.get('youtube_url')}"]
        return "\n".join(lines)


def list_projects(limit: int = 20) -> list[dict]:
    """Most recent projects, newest first."""
    if not PROJECTS_DIR.exists():
        return []

    out = []
    for path in sorted(PROJECTS_DIR.glob("*.json"), reverse=True)[:limit]:
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        out.append(
            {
                "path": str(path),
                "project_id": data.get("project_id", path.stem),
                "topic": data.get("topic", ""),
                "format": data.get("format", ""),
                "title": data.get("youtube_title", ""),
                "url": data.get("youtube_url", ""),
            }
        )
    return out
