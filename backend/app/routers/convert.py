"""繁简转换接口。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.converter import to_simplified, to_traditional

router = APIRouter(prefix="/convert", tags=["convert"])


class ConvertRequest(BaseModel):
    text: str
    direction: str = "t2s"  # t2s: 繁转简, s2t: 简转繁


class ConvertResponse(BaseModel):
    text: str
    direction: str


@router.post("", response_model=ConvertResponse)
def convert_text(payload: ConvertRequest) -> ConvertResponse:
    """繁简文字转换。

    - direction=t2s：繁体转简体（默认）
    - direction=s2t：简体转繁体
    """
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")

    direction = payload.direction.lower()
    if direction == "t2s":
        result = to_simplified(payload.text)
    elif direction == "s2t":
        result = to_traditional(payload.text)
    else:
        raise HTTPException(status_code=400, detail="direction 仅支持 t2s 或 s2t")

    return ConvertResponse(text=result, direction=direction)
