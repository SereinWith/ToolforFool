"""搜索相关 schema。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class SearchRequest(BaseModel):
    """搜索请求：多关键词 + URL 列表。"""

    keywords: list[str]
    # 手动指定的古籍 URL 列表；若为空则从已入库的 sources 中检索
    urls: list[HttpUrl] | None = None


class SearchResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    keyword: str
    source_url: str
    source_title: str | None
    site: str | None
    excerpt: str
    matched_keyword: str
    created_at: datetime
