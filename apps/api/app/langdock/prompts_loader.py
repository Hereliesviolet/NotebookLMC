"""Loads prompt templates from packages/prompts.

In Docker, packages/prompts is mounted read-only at /app/packages/prompts
(see docker-compose.yml). For local (non-Docker) development, we fall back
to the relative path from the repo root.
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


def _candidate_dirs() -> list[Path]:
    candidates = [Path("/app/packages/prompts")]
    here = Path(__file__).resolve()
    for parent in here.parents:
        repo_root_guess = parent / "packages" / "prompts"
        if repo_root_guess not in candidates:
            candidates.append(repo_root_guess)
    return candidates


def _prompts_dir() -> Path:
    override = os.environ.get("PROMPTS_DIR")
    if override:
        return Path(override)
    for candidate in _candidate_dirs():
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not locate packages/prompts in any of: {_candidate_dirs()}")


@lru_cache
def load_prompt(name: str) -> str:
    """`name` is the filename without extension, e.g. 'system_final_answer'."""
    path = _prompts_dir() / f"{name}.md"
    return path.read_text(encoding="utf-8").strip()


@lru_cache
def load_output_schema() -> str:
    path = _prompts_dir() / "output_schema.json"
    return path.read_text(encoding="utf-8").strip()


@lru_cache
def load_final_answer_tool() -> dict[str, Any]:
    """Anthropic tool definition (name/description/input_schema) for the final
    chat answer - passed as `tools=[...]` with `tool_choice={"type": "tool", ...}`
    so the model's JSON is parsed/validated server-side instead of as free text.
    """
    path = _prompts_dir() / "final_answer_tool_schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def load_tool_schema(name: str) -> dict[str, Any]:
    """`name` is the filename without extension, e.g. 'studio_summary_tool_schema'.

    Generic counterpart to load_final_answer_tool() - used for the Studio
    artifact tools (summary/faq/timeline/briefing).
    """
    path = _prompts_dir() / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))
