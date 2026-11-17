"""OCR 文字识别服务（阶段三）。

支持 PaddleOCR（本地）与云 API（预留）。
PaddleOCR 为可选依赖，未安装时接口返回提示信息。
"""
from __future__ import annotations

import io
import os
from abc import ABC, abstractmethod

# PaddlePaddle 3.x 在 CPU 上 oneDNN 与 PIR 执行器存在兼容问题，
# 需在导入 paddleocr 之前禁用 MKLDNN 默认启用。
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")

from app.config import settings


class OCRService(ABC):
    """OCR 服务抽象基类。"""

    @abstractmethod
    def recognize(self, image_bytes: bytes) -> str:
        """识别图片中的文字，返回纯文本。"""

    @property
    @abstractmethod
    def available(self) -> bool:
        """服务是否可用。"""


class PaddleOCRService(OCRService):
    """本地 PaddleOCR 实现（可选依赖）。"""

    def __init__(self) -> None:
        self._ocr = None
        try:
            from paddleocr import PaddleOCR  # type: ignore

            # use_textline_orientation=True 支持方向分类，lang='ch' 中文
            # PaddleOCR 3.x：use_angle_cls 已废弃，改用 use_textline_orientation
            self._ocr = PaddleOCR(use_textline_orientation=True, lang="ch")
        except Exception:
            self._ocr = None

    @property
    def available(self) -> bool:
        return self._ocr is not None

    def recognize(self, image_bytes: bytes) -> str:
        if not self.available:
            raise RuntimeError(
                "PaddleOCR 未安装。请运行 pip install paddleocr paddlepaddle，"
                "或在 .env 中配置 OCR_PROVIDER=cloud 并设置云 OCR 的 API Key。"
            )
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        # PaddleOCR 3.x：ocr() 不再接受 cls 参数，方向分类在构造时已开启
        result = self._ocr.ocr(np.array(img))
        lines: list[str] = []
        # PaddleOCR 3.x 返回 OCRResult（行为类似 dict），rec_texts 为识别文本列表
        if result and result[0]:
            ocr_result = result[0]
            rec_texts = ocr_result.get("rec_texts") if hasattr(ocr_result, "get") else None
            if rec_texts:
                lines = [t for t in rec_texts if t]
        return "\n".join(lines)


class CloudOCRService(OCRService):
    """云 OCR 实现（预留接口，后续接入百度/阿里等）。"""

    def __init__(self) -> None:
        self.api_key = settings.ocr_api_key

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def recognize(self, image_bytes: bytes) -> str:
        if not self.available:
            raise RuntimeError("未配置 OCR_API_KEY，云 OCR 服务不可用")
        # TODO: 接入具体云 OCR API
        raise NotImplementedError("云 OCR 接口尚未实现，请配置 OCR_PROVIDER=paddle 并安装 PaddleOCR")


def get_ocr_service() -> OCRService:
    """根据配置返回 OCR 服务实例。"""
    if settings.ocr_provider.lower() == "cloud":
        return CloudOCRService()
    return PaddleOCRService()
