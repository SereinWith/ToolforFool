"""搜索结果数据模型（阶段二：临时存储含关键词的古籍选段）。"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SearchResult(Base):
    __tablename__ = "search_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    site: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # 含关键词的选段，保留上下文
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    # 命中的关键词（可能与输入关键词不完全一致，如子串匹配）
    matched_keyword: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
