"""Loads prompt templates from packages/prompts - mirrored from the api service."""

import os
from functools import lru_cache
from pathlib import Path


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
    path = _prompts_dir() / f"{name}.md"
    return path.read_text(encoding="utf-8").strip()
