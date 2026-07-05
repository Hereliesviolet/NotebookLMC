"""Studio artifact response schema (architecture doc §19/§26.5).

`content` is intentionally a generic dict - its shape differs per artifact
type (see packages/prompts/studio_*_tool_schema.json for the schema Sonnet's
tool-use output is validated against).
"""
from datetime import datetime

from pydantic import BaseModel


class StudioArtifactOut(BaseModel):
    id: str
    notebook_id: str
    type: str
    content: dict
    source_ids: list[str]
    model: str | None
    created_at: datetime
    updated_at: datetime
