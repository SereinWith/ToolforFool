"""人物时间线服务（阶段三）：从古籍正文中提取人物与事件。"""
from __future__ import annotations

import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.person import PersonEvent
from app.models.source import Source

# 常见朝代与历史时期，用于时间线索提取
_DYNASTIES = [
    "夏", "商", "周", "西周", "东周", "春秋", "战国",
    "秦", "汉", "西汉", "东汉", "三国", "魏", "蜀", "吴",
    "晋", "西晋", "东晋", "南北朝", "南朝", "北朝",
    "隋", "唐", "五代", "宋", "北宋", "南宋", "辽", "金", "西夏",
    "元", "明", "清",
]

# 古籍中常见的人名触发模式
_NAME_PATTERNS = [
    r"([\u4e00-\u9fa5]{2,4})曰",      # X曰
    r"([\u4e00-\u9fa5]{2,4})为",      # X为
    r"帝([\u4e00-\u9fa5]{1,3})",      # 帝X
    r"王([\u4e00-\u9fa5]{1,3})",      # 王X
    r"([\u4e00-\u9fa5]{2,4})氏",      # X氏
]

# 单字停用词，避免误提取
_STOP_WORDS = {
    "之", "其", "此", "彼", "何", "孰", "焉", "也", "矣", "乎", "哉", "耶",
    "者", "所", "以", "于", "为", "而", "则", "乃", "且", "或", "若", "如",
    "曰", "云", "言", "谓", "是", "非", "有", "无", "不", "未", "莫", "勿",
    "吾", "我", "余", "予", "汝", "尔", "子", "君", "公", "卿", "夫",
    "天", "地", "人", "民", "国", "家", "王", "帝", "侯", "伯", "子男",
    "文", "武", "成", "康", "昭", "穆", "共", "懿", "孝", "惠", "怀", "湣",
    "黄帝", "炎帝", "颛顼", "帝喾", "尧", "舜", "禹", "汤", "桀", "纣",
}


def extract_person_names(text: str, min_len: int = 2, max_len: int = 4) -> list[str]:
    """从文本中提取人名（规则匹配，去重保序）。"""
    names: list[str] = []
    seen: set[str] = set()

    for pattern in _NAME_PATTERNS:
        for match in re.finditer(pattern, text):
            name = match.group(1)
            if (
                name
                and min_len <= len(name) <= max_len
                and name not in _STOP_WORDS
                and name not in seen
            ):
                seen.add(name)
                names.append(name)

    # 额外：匹配"太史公曰"中的"太史公"等称谓
    for match in re.finditer(r"([\u4e00-\u9fa5]{2,4})公曰", text):
        name = match.group(1) + "公"
        if name not in seen:
            seen.add(name)
            names.append(name)

    return names


def extract_time_ref(text: str) -> str | None:
    """提取时间线索（朝代/时期）。"""
    for dynasty in _DYNASTIES:
        if dynasty in text:
            return dynasty
    return None


def extract_person_events(text: str, source_url: str, source_title: str | None) -> list[dict]:
    """从正文中提取人物事件。

    对每个人名，找到其所在句子作为事件描述。
    """
    names = extract_person_names(text)
    if not names:
        return []

    # 按句/段切分
    sentences = re.split(r"[。！？；\n]", text)
    events: list[dict] = []
    for name in names:
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if name in sent:
                events.append(
                    {
                        "person_name": name,
                        "event_text": sent,
                        "time_ref": extract_time_ref(sent),
                        "source_url": source_url,
                        "source_title": source_title,
                    }
                )
    return events


def build_timeline(db: Session, source_ids: list[int] | None = None) -> list[PersonEvent]:
    """从已入库文献中构建人物时间线。

    - source_ids 为空时，处理全部已入库文献；
    - 结果写入 person_events 表（先清空）。
    """
    db.query(PersonEvent).delete()

    query = db.query(Source)
    if source_ids:
        query = query.filter(Source.id.in_(source_ids))
    sources = query.all()

    saved: list[PersonEvent] = []
    for source in sources:
        text = source.content or source.summary or ""
        if not text:
            continue
        events = extract_person_events(text, source.url, source.title)
        for ev in events:
            item = PersonEvent(**ev)
            db.add(item)
            saved.append(item)

    db.commit()
    for item in saved:
        db.refresh(item)
    return saved


def get_persons(db: Session) -> list[dict]:
    """获取所有人物及其事件数量。"""
    rows = (
        db.query(
            PersonEvent.person_name,
            func.count(PersonEvent.id).label("count"),
        )
        .group_by(PersonEvent.person_name)
        .order_by(func.count(PersonEvent.id).desc())
        .all()
    )
    return [{"name": r[0], "event_count": r[1]} for r in rows]


def get_person_events(db: Session, person_name: str) -> list[PersonEvent]:
    """获取某人物的所有事件，按时间线索排序。"""
    return (
        db.query(PersonEvent)
        .filter(PersonEvent.person_name == person_name)
        .order_by(PersonEvent.time_ref.asc(), PersonEvent.id.asc())
        .all()
    )
