"""人物时间线接口（阶段三）。"""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.timeline import build_timeline, get_person_events, get_persons

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.post("/build")
def build(
    source_ids: list[int] | None = Body(default=None, embed=True),
    db: Session = Depends(get_db),
) -> dict:
    """从已入库文献中构建人物时间线。"""
    events = build_timeline(db, source_ids)
    persons = get_persons(db)
    return {"event_count": len(events), "person_count": len(persons), "persons": persons}


@router.get("/persons")
def list_persons(db: Session = Depends(get_db)) -> list[dict]:
    """获取所有人物及其事件数量。"""
    return get_persons(db)


@router.get("/persons/{person_name}")
def person_events(person_name: str, db: Session = Depends(get_db)) -> list[dict]:
    """获取某人物的所有事件（时间线）。"""
    events = get_person_events(db, person_name)
    if not events:
        raise HTTPException(status_code=404, detail=f"未找到人物「{person_name}」的事件")
    return [
        {
            "id": e.id,
            "person_name": e.person_name,
            "event_text": e.event_text,
            "time_ref": e.time_ref,
            "source_url": e.source_url,
            "source_title": e.source_title,
            "created_at": e.created_at,
        }
        for e in events
    ]
