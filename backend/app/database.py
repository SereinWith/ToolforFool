"""数据库连接与会话管理。"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite 需要 check_same_thread=False
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表（开发期直接 create_all，后续可替换为 Alembic 迁移）。"""
    # 确保模型被注册
    from app.models import source  # noqa: F401
    from app.models.person import PersonEvent  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_person_events()


def _migrate_person_events() -> None:
    """轻量迁移：为已存在的 person_events 表补充 origin 列。"""
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as conn:
        cols = conn.exec_driver_sql("PRAGMA table_info(person_events)").fetchall()
        if not cols:
            return
        names = {row[1] for row in cols}
        if "origin" not in names:
            conn.exec_driver_sql(
                "ALTER TABLE person_events ADD COLUMN origin VARCHAR(16) NOT NULL DEFAULT 'auto'"
            )
