"""AI 能力接口（阶段三）：语义模糊搜索、OCR、内容摘要。"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.search import SearchRequest, SearchResultOut
from app.services.ai import expand_keywords, get_llm_service, summarize_text
from app.services.ocr import get_ocr_service
from app.services.search import run_search

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/search", response_model=list[SearchResultOut])
def ai_search(payload: SearchRequest, db: Session = Depends(get_db)):
    """语义模糊搜索：先用 AI 扩展关键词，再执行检索。"""
    if not payload.keywords:
        raise HTTPException(status_code=400, detail="请输入至少一个关键词")

    llm = get_llm_service()
    expanded: list[str] = []
    for kw in payload.keywords:
        expanded.extend(expand_keywords(kw, llm))
    # 去重保序
    seen = set()
    keywords = []
    for kw in expanded:
        if kw not in seen:
            seen.add(kw)
            keywords.append(kw)

    urls = [str(u) for u in payload.urls] if payload.urls else None
    results = run_search(db, keywords, urls)
    return results


@router.post("/ocr")
async def ocr_recognize(file: UploadFile = File(...)) -> dict:
    """OCR 文字识别：上传图片，返回识别出的文字。"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="图片内容为空")

    ocr = get_ocr_service()
    if not ocr.available:
        raise HTTPException(
            status_code=503,
            detail="OCR 服务不可用。请任选其一：配置 AI_API_KEY（视觉大模型）、"
            "配置 BAIDU_OCR_API_KEY/BAIDU_OCR_SECRET_KEY（百度云 OCR）、"
            "或安装 PaddleOCR（pip install -r requirements-ocr.txt）。",
        )
    try:
        text = ocr.recognize(image_bytes)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"OCR 识别失败: {exc}") from exc

    return {"filename": file.filename, "text": text, "provider": ocr.name}


@router.post("/summarize")
def ai_summarize(text: str) -> dict:
    """AI 内容摘要。"""
    if not text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")
    llm = get_llm_service()
    summary = summarize_text(text, llm)
    return {"summary": summary, "used_ai": llm.available}


@router.get("/status")
def ai_status() -> dict:
    """查看 AI 与 OCR 服务可用状态。"""
    llm = get_llm_service()
    ocr = get_ocr_service()
    return {
        "llm_provider": llm.__class__.__name__,
        "llm_available": llm.available,
        "ocr_provider": ocr.name,
        "ocr_available": ocr.available,
        "ocr_configured": settings.ocr_provider,
        "auto_simplify": settings.auto_simplify,
    }
