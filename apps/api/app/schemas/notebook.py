from datetime import datetime

from pydantic import BaseModel


class NotebookCreate(BaseModel):
    title: str
    description: str | None = None
    visibility: str = "private"


class NotebookUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    visibility: str | None = None


class NotebookOut(BaseModel):
    id: str
    owner_id: str
    title: str
    description: str | None
    visibility: str
    source_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
