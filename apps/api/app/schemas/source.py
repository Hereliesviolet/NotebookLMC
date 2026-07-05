from datetime import datetime

from pydantic import BaseModel


class SourceOut(BaseModel):
    id: str
    notebook_id: str
    filename: str
    original_filename: str
    mime_type: str
    status: str
    page_count: int | None
    token_count: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SourceUploadResponse(BaseModel):
    source: SourceOut
    job_id: str
