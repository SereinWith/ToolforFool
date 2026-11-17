"""搜索与导出接口（阶段二）。"""
import csv
import io
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.search import SearchRequest, SearchResultOut
from app.services.search import get_results, run_search

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=list[SearchResultOut])
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    """多关键词检索：在指定 URL 或已入库文献中查找含关键词的选段。"""
    urls = [str(u) for u in payload.urls] if payload.urls else None
    results = run_search(db, payload.keywords, urls)
    return results


@router.get("/results", response_model=list[SearchResultOut])
def list_results(keyword: str | None = None, db: Session = Depends(get_db)):
    """获取上一次搜索的结果。"""
    return get_results(db, keyword)


@router.get("/export")
def export_results(
    format: str = Query("json", pattern="^(json|csv|txt)$"),
    db: Session = Depends(get_db),
):
    """导出搜索结果。"""
    results = get_results(db)
    data = [
        {
            "keyword": r.keyword,
            "source_title": r.source_title or "",
            "site": r.site or "",
            "source_url": r.source_url,
            "excerpt": r.excerpt,
            "matched_keyword": r.matched_keyword,
        }
        for r in results
    ]

    if format == "json":
        body = json.dumps(data, ensure_ascii=False, indent=2)
        return Response(
            content=body,
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="search_results.json"'},
        )

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(data[0].keys()) if data else [])
        if data:
            writer.writeheader()
            writer.writerows(data)
        return Response(
            content=output.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="search_results.csv"'},
        )

    # txt
    lines = []
    for item in data:
        lines.append(f"【关键词】{item['keyword']}")
        lines.append(f"【来源】{item['source_title']} ({item['site']})")
        lines.append(f"【网址】{item['source_url']}")
        lines.append(f"【选段】{item['excerpt']}")
        lines.append("-" * 40)
    body = "\n".join(lines)
    # 加 BOM 以便 Windows 记事本正确识别 UTF-8
    return Response(
        content="\ufeff" + body,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="search_results.txt"'},
    )
