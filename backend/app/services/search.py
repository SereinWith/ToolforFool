"""搜索服务：多关键词检索 + 含关键词选段提取。"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.crawler.registry import crawl_and_extract
from app.models.search_result import SearchResult
from app.models.source import Source


def _extract_excerpts(text: str, keyword: str, context_chars: int = 60) -> list[str]:
    """在正文中查找关键词，返回带上下文的选段列表。

    以关键词为中心，前后各取 context_chars 个字符作为上下文。
    """
    excerpts: list[str] = []
    if not text or not keyword:
        return excerpts

    # 简单子串匹配（不区分大小写对中文无影响，对英文关键词友好）
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    for match in pattern.finditer(text):
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        snippet = text[start:end]
        # 截断处补充省略号
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        excerpts.append(snippet)
    return excerpts


def search_in_text(title: str | None, url: str, site: str | None, text: str, keywords: list[str]) -> list[dict]:
    """在单篇正文中检索多个关键词，返回选段记录列表。"""
    results: list[dict] = []
    for keyword in keywords:
        keyword = keyword.strip()
        if not keyword:
            continue
        excerpts = _extract_excerpts(text, keyword)
        for excerpt in excerpts:
            results.append(
                {
                    "keyword": keyword,
                    "source_url": url,
                    "source_title": title,
                    "site": site,
                    "excerpt": excerpt,
                    "matched_keyword": keyword,
                }
            )
    return results


def run_search(db: Session, keywords: list[str], urls: list[str] | None = None) -> list[SearchResult]:
    """执行搜索，结果写入 search_results 表并返回。

    - 若提供 urls，则抓取这些 URL 的正文后检索；
    - 否则从已入库的 sources 表中检索正文。
    """
    # 清空上一次的搜索结果（临时存储）
    db.query(SearchResult).delete()

    records: list[dict] = []

    if urls:
        # 抓取指定 URL
        for url in urls:
            url = str(url).strip()
            if not url:
                continue
            try:
                info = crawl_and_extract(url)
            except Exception:  # noqa: BLE001
                # 单个 URL 抓取失败不影响其他
                continue
            text = info.get("content") or info.get("summary") or ""
            records.extend(
                search_in_text(info.get("title"), info["url"], info.get("site"), text, keywords)
            )
    else:
        # 从已入库 sources 检索
        sources = db.query(Source).all()
        for source in sources:
            text = source.content or source.summary or ""
            records.extend(
                search_in_text(source.title, source.url, source.site, text, keywords)
            )

    # 写入临时存储
    saved: list[SearchResult] = []
    for rec in records:
        item = SearchResult(**rec)
        db.add(item)
        saved.append(item)
    db.commit()
    for item in saved:
        db.refresh(item)
    return saved


def get_results(db: Session, keyword: str | None = None) -> list[SearchResult]:
    query = db.query(SearchResult)
    if keyword:
        query = query.filter(SearchResult.keyword == keyword)
    return query.order_by(SearchResult.created_at.desc()).all()
