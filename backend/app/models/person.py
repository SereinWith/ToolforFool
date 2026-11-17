"""人物时间线数据模型（阶段三）。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PersonEvent(Base):
    """人物事件：从古籍中提取的某人物相关事件。"""

    __tablename__ = "person_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # 事件描述（含人物的句子/段落）
    event_text: Mapped[str] = mapped_column(Text, nullable=False)
    # 时间线索（如朝代、年号、干支等，可能为空）
    time_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # 来源 URL 与标题
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
