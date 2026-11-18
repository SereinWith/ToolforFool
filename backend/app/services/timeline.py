"""人物时间线服务：从古籍正文中提取人物与事件。

混合方案：
- 配置了 AI_API_KEY 时，优先用大模型做结构化抽取（人物 / 事迹 / 朝代）；
- 无 Key 或调用失败时，降级为规则 + 词表抽取；
- 公共能力：别称归并、虚词过滤、朝代年代序排序、重建时保留人工数据。
"""
from __future__ import annotations

import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.person import PersonEvent
from app.models.source import Source
from app.services.ai import extract_events_with_ai, get_llm_service

# ===== 朝代与年代顺序 =====
_DYNASTY_SEQUENCE = [
    "上古", "三皇", "五帝",
    "夏", "商", "周", "西周", "东周", "春秋", "战国",
    "秦", "汉", "西汉", "东汉", "三国", "魏", "蜀", "吴",
    "晋", "西晋", "东晋", "南北朝", "南朝", "北朝",
    "隋", "唐", "五代", "北宋", "南宋", "辽", "金", "西夏",
    "元", "明", "清",
]
_DYNASTY_RANK = {name: idx for idx, name in enumerate(_DYNASTY_SEQUENCE)}

# 多字朝代名可安全直接匹配；单字朝代名必须带上下文（唐朝、汉代、明末…），
# 否则「聪明」「陶唐」这类词语会造成误判。
_MULTI_CHAR_DYNASTIES = [d for d in _DYNASTY_SEQUENCE if len(d) >= 2]
_SINGLE_CHAR_DYNASTY_RE = re.compile(
    r"(夏|商|周|秦|汉|晋|隋|唐|宋|辽|金|元|明|清)(?=朝|代|之[初末时世]|末|初|年|时|世|王|帝|武|文)"
)

# 篇名中的时间线索（如《史记·五帝本纪》）
_TITLE_TIME_HINTS: dict[str, str] = {
    "五帝": "五帝", "夏本纪": "夏", "殷本纪": "商", "周本纪": "西周",
    "秦本纪": "秦", "秦始皇": "秦", "项羽": "秦",
    "高祖": "西汉", "吕太后": "西汉", "孝文": "西汉", "孝武": "西汉",
    "论语": "春秋", "左传": "春秋", "孟子": "战国", "庄子": "战国",
    "诗经": "西周", "楚辞": "战国", "汉书": "东汉", "三国志": "三国",
    "晋书": "晋", "唐书": "唐", "宋史": "宋", "明史": "明", "清史": "清",
}

# ===== 人名别称归并 =====
_ALIAS_GROUPS: dict[str, list[str]] = {
    "黄帝": ["轩辕", "轩辕氏", "有熊", "有熊氏", "公孙轩辕", "帝鸿", "帝鸿氏"],
    "炎帝": ["神农", "神农氏", "烈山", "烈山氏"],
    "少昊": ["少皞", "少皓"],
    "颛顼": ["帝颛顼", "高阳", "高阳氏"],
    "帝喾": ["喾", "高辛", "高辛氏"],
    "尧": ["帝尧", "唐尧", "放勋"],
    "舜": ["帝舜", "虞舜", "重华"],
    "禹": ["大禹", "夏禹", "帝禹", "文命"],
    "汤": ["商汤", "成汤", "天乙"],
    "孔子": ["孔丘", "仲尼", "孔夫子", "孔仲尼"],
    "老子": ["李耳", "老聃"],
    "庄子": ["庄周", "南华真人"],
    "孟子": ["孟轲", "亚圣"],
    "韩非": ["韩非子"],
    "屈原": ["屈平", "三闾大夫"],
    "司马迁": ["太史公", "太史", "子长"],
    "秦始皇": ["嬴政", "赵政", "始皇帝"],
    "项羽": ["项籍", "西楚霸王"],
    "刘邦": ["汉高祖", "沛公", "刘季"],
    "周公": ["姬旦", "周公旦"],
    "周文王": ["西伯昌", "姬昌"],
    "周武王": ["姬发"],
    "李白": ["李太白", "青莲居士", "诗仙"],
    "杜甫": ["杜子美", "少陵野老", "诗圣"],
    "苏轼": ["苏东坡", "苏子瞻", "东坡居士"],
}

# 别称 → 主名
_CANONICAL: dict[str, str] = {
    alias: canonical
    for canonical, aliases in _ALIAS_GROUPS.items()
    for alias in aliases
}
_CANONICAL.update({canonical: canonical for canonical in _ALIAS_GROUPS})

# ===== 过滤词表 =====
# 虚词：出现在人名中即判定为非人名
_FUNCTION_CHARS = set("之于以为而则乃且若虽故因由是与及以其此彼何孰焉也矣乎哉耶者所")
# 动词/数量词等非人名字符（用于剔除「谁可」「姓姒」「娶某」「谓四岳」一类误匹配）
_NON_NAME_CHARS = set("生娶姓谓召问言谁可能使有无不未莫勿欲从皆咸亦又遂尽举共相十族讼讴赞隐离本昔觐应远")
_NON_NAME_CHARS |= _FUNCTION_CHARS
# 常见非人名词组（规则抽取时直接排除）
_STOP_WORDS = {
    "之", "其", "此", "彼", "何", "孰", "焉", "也", "矣", "乎", "哉", "耶",
    "者", "所", "以", "于", "为", "而", "则", "乃", "且", "或", "若", "如",
    "曰", "云", "言", "谓", "是", "非", "有", "无", "不", "未", "莫", "勿",
    "吾", "我", "余", "予", "汝", "尔", "子", "君", "公", "卿", "夫",
    "天", "地", "人", "民", "国", "家", "王", "帝", "侯", "伯",
    "文", "武", "成", "康", "昭", "穆", "共", "懿", "孝", "惠", "怀", "湣",
}
_COMMON_WORDS = {
    # 虚词组合
    "于是", "是以", "然后", "由此", "何以", "何为", "所谓", "未知", "不可",
    "不能", "未有", "无有", "不以", "不足", "不如", "若是", "若此", "其次",
    "其一", "其二", "其三", "数日", "数年", "明年", "是岁", "当时", "此时",
    "其后", "其后", "自此", "自幼", "少时", "既而", "俄而", "顷之", "久之",
    # 泛指与身份
    "天下", "国家", "社稷", "宗庙", "朝廷", "四方", "万民", "众人", "百姓",
    "诸侯", "天子", "帝王", "皇帝", "大王", "先王", "先生", "君子", "小人",
    "大夫", "将军", "丞相", "太守", "陛下", "足下", "寡人", "父子", "兄弟",
    "夫妇", "师徒", "中原", "中国", "后世", "上古", "百官", "文祖", "四岳",
    "狱讼", "讴歌", "十六族", "三族", "九族", "万国",
    # X者 误匹配
    "前者", "后者", "二者", "三者", "四者", "五者", "来者", "使者", "学者",
    "王者", "长者", "幼者", "死者", "生者", "行者", "侍者", "从者", "御者",
    "渔者", "耕者", "隐者", "智者", "愚者", "圣者", "贤者", "仁者", "勇者",
}

# 人名触发模式（去掉 "X为" 与 "王X"，这两类误匹配率过高）
_NAME_PATTERNS = [
    r"([\u4e00-\u9fa5]{2,3})曰",      # X曰
    r"([\u4e00-\u9fa5]{2,3})者",      # X者（如「黄帝者」）
    r"([\u4e00-\u9fa5]{2,3})氏",      # X氏
    # 帝X 需后接常见谓语，避免把「炎帝欲侵」截成「欲侵」
    r"帝([\u4e00-\u9fa5]{1,2})(?=者|曰|立|崩|时|之|即|为|乃|而|生|子)",
]

# 候选名尾部误粘的称谓字（保留「子」，避免误伤孔子、孟子等）
_STRIP_SUFFIX_CHARS = "父母兄弟妻皆咸亦又乃遂尽举共相"

_MAX_EVENTS_PER_PERSON = 40
_MAX_TOTAL_EVENTS = 3000


def _clean_candidate(name: str) -> str:
    """清理候选名：优先识别后缀中的已知别称，再去掉误粘的称谓字。"""
    for alias, canonical in _CANONICAL.items():
        if len(alias) >= 2 and name != alias and name.endswith(alias):
            return canonical
    while name and name[-1] in _STRIP_SUFFIX_CHARS:
        name = name[:-1]
    return name


def canonical_name(name: str) -> str:
    """别称归并为主名。"""
    return _CANONICAL.get(name, name)


def _is_valid_name(name: str) -> bool:
    if not (2 <= len(name) <= 4):
        return False
    if name in _STOP_WORDS or name in _COMMON_WORDS:
        return False
    # 含虚词直接排除，可挡掉「于是」「以为」「无为」等
    if any(ch in _FUNCTION_CHARS for ch in name):
        return False
    if any(ch in _NON_NAME_CHARS for ch in name):
        return False
    return True


def extract_person_names(text: str, min_len: int = 2, max_len: int = 4) -> list[str]:
    """规则抽取人名（去重保序，已做别称归并与噪声过滤）。

    保留条件：命中「曰/者/氏/帝X」等强模式，或在正文中出现至少 2 次。
    """
    candidates: list[tuple[str, bool]] = []  # (候选名, 是否强模式)

    for pattern in _NAME_PATTERNS:
        for match in re.finditer(pattern, text):
            candidates.append((match.group(1), True))

    # 已知别称/主名：只要出现一次就纳入
    for canonical, aliases in _ALIAS_GROUPS.items():
        if canonical in text or any(alias in text for alias in aliases):
            candidates.append((canonical, True))

    names: list[str] = []
    seen: set[str] = set()
    for raw_name, strong in candidates:
        name = canonical_name(_clean_candidate(raw_name))
        # 已知人物允许单字主名（尧、舜、禹、汤、喾等）
        if name not in _ALIAS_GROUPS and not (min_len <= len(name) <= max_len):
            continue
        if not _is_valid_name(name) and name not in _ALIAS_GROUPS:
            continue
        if not strong and text.count(name) < 2:
            continue
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def extract_time_ref(text: str, title: str | None = None) -> str | None:
    """提取时间线索：优先篇名提示（如「五帝本纪」），其次正文中的朝代上下文。"""
    if title:
        for hint, dynasty in _TITLE_TIME_HINTS.items():
            if hint in title:
                return dynasty
    if not text:
        return None

    candidates: list[tuple[int, str]] = []
    for dynasty in _MULTI_CHAR_DYNASTIES:
        pos = text.find(dynasty)
        if pos != -1:
            candidates.append((pos, dynasty))
    for match in _SINGLE_CHAR_DYNASTY_RE.finditer(text):
        candidates.append((match.start(), match.group(1)))

    if not candidates:
        return None
    # 位置更靠前优先；同位置时取更长的名称（如「西周」优于「周」）
    candidates.sort(key=lambda item: (item[0], -len(item[1])))
    return candidates[0][1]


def extract_person_events(
    text: str,
    source_url: str,
    source_title: str | None,
    doc_time: str | None = None,
) -> list[dict]:
    """规则抽取人物事件：把含某人物（含别称）的句子归为其事迹。"""
    names = extract_person_names(text)
    if not names:
        return []

    sentences = [s.strip() for s in re.split(r"[。！？；\n]", text) if s.strip()]
    doc_time = doc_time or extract_time_ref(text, source_title)

    events: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for name in names:
        variants = [name, *(_ALIAS_GROUPS.get(name, []))]
        count = 0
        for sent in sentences:
            if len(sent) < 4 or len(sent) > 400:
                continue
            if not any(v in sent for v in variants):
                continue
            key = (name, sent)
            if key in seen:
                continue
            seen.add(key)
            events.append(
                {
                    "person_name": name,
                    "event_text": sent,
                    "time_ref": extract_time_ref(sent) or doc_time,
                    "source_url": source_url,
                    "source_title": source_title,
                    "origin": "auto",
                }
            )
            count += 1
            if count >= _MAX_EVENTS_PER_PERSON:
                break
    return events


def _ai_person_events(text: str, source: Source, doc_time: str | None) -> list[dict]:
    """AI 抽取人物事件，失败返回空列表由规则兜底。"""
    llm = get_llm_service()
    if not llm.available:
        return []

    raw_events = extract_events_with_ai(text, llm)
    if not raw_events:
        return []

    events: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for raw in raw_events:
        person = canonical_name(raw.get("person", "").strip())
        event = raw.get("event", "").strip()
        if not person or not event:
            continue
        event = event[:300]
        key = (person, event)
        if key in seen:
            continue
        seen.add(key)
        events.append(
            {
                "person_name": person,
                "event_text": event,
                "time_ref": raw.get("time") or extract_time_ref(event) or doc_time,
                "source_url": source.url,
                "source_title": source.title,
                "origin": "auto",
            }
        )
    return events


def build_timeline(
    db: Session, source_ids: list[int] | None = None
) -> tuple[list[PersonEvent], str]:
    """从已入库文献中构建人物时间线。

    - 优先使用 AI 抽取，未配置 Key 或失败时降级为规则抽取；
    - 只清除 origin=auto 的旧数据，保留人工补录（origin=manual）。
    """
    db.query(PersonEvent).filter(PersonEvent.origin == "auto").delete(synchronize_session=False)

    query = db.query(Source)
    if source_ids:
        query = query.filter(Source.id.in_(source_ids))
    sources = query.all()

    saved: list[PersonEvent] = []
    used_ai = False
    for source in sources:
        text = source.content or source.summary or ""
        if not text:
            continue

        doc_time = extract_time_ref(text, source.title)
        events = _ai_person_events(text, source, doc_time)
        if events:
            used_ai = True
        else:
            events = extract_person_events(text, source.url, source.title, doc_time)

        for ev in events:
            if len(saved) >= _MAX_TOTAL_EVENTS:
                break
            item = PersonEvent(**ev)
            db.add(item)
            saved.append(item)

    db.commit()
    for item in saved:
        db.refresh(item)
    return saved, ("ai" if used_ai else "rule")


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
    """获取某人物的所有事件，按朝代年代序排序。"""
    events = (
        db.query(PersonEvent)
        .filter(PersonEvent.person_name == person_name)
        .all()
    )
    events.sort(key=lambda e: (_DYNASTY_RANK.get(e.time_ref or "", 99), e.id))
    return events
