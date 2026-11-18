"""来源数据接口：抓取并记录 URL + 概述（第一档）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.crawler.registry import crawl_and_extract
from app.database import get_db
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceOut
from app.services.converter import to_simplified

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)) -> list[Source]:
    return db.query(Source).order_by(Source.crawled_at.desc()).all()


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: int, db: Session = Depends(get_db)) -> Source:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="记录不存在")
    return source


@router.post("/crawl", response_model=SourceOut)
def crawl_url(payload: SourceCreate, db: Session = Depends(get_db)) -> Source:
    """抓取指定 URL，按站点适配器提取标题/概述/正文并入库。"""
    url = str(payload.url)
    try:
        info = crawl_and_extract(url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"抓取失败: {exc}") from exc

    title = info["title"] or payload.title
    summary = info["summary"] or payload.summary
    content = info["content"] or payload.content
    site = info["site"] or payload.site

    # 录入时自动繁体转简体（默认开启，可通过 AUTO_SIMPLIFY=false 关闭）
    if settings.auto_simplify:
        title = to_simplified(title) if title else title
        summary = to_simplified(summary) if summary else summary
        content = to_simplified(content) if content else content

    source = Source(
        url=info["url"],
        title=title,
        summary=summary,
        content=content,
        site=site,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: Session = Depends(get_db)) -> None:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(source)
    db.commit()
