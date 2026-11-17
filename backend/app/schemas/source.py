"""Source 相关 schema。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class SourceCreate(BaseModel):
    url: HttpUrl
    title: str | None = None
    summary: str | None = None
    content: str | None = None
    site: str | None = None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: str | None
    summary: str | None
    content: str | None
    site: str | None
    crawled_at: datetime
