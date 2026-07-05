from datetime import datetime

from pydantic import BaseModel


class NoteCreate(BaseModel):
    title: str
    content: str
    source_refs_json: dict | list | None = None


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    source_refs_json: dict | list | None = None


class NoteOut(BaseModel):
    id: str
    notebook_id: str
    title: str
    content: str
    source_refs_json: dict | list | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
