"""Chat request/response schemas.

The response schema mirrors packages/prompts/output_schema.json
exactly, so the LLM's structured output can be validated and passed through
with minimal transformation.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    source_ids: list[str] | None = None
    mode: Literal["grounded"] = "grounded"


class Citation(BaseModel):
    source_id: str
    chunk_id: str
    document_name: str
    page_start: int | None = None
    page_end: int | None = None
    quote: str
    supports_claim: str | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    confidence: Literal["low", "medium", "high"] = "medium"
    missing_information: list[str] = []
    follow_up_questions: list[str] = []


class MessageOut(BaseModel):
    id: str
    notebook_id: str
    role: str
    content: str
    model: str | None
    citations_json: dict | list | None
    created_at: datetime

    class Config:
        from_attributes = True
