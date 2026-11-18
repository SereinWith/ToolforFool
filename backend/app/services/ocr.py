"""OCR 文字识别服务。

支持三种引擎，按配置或自动优先级选择：
1. vision：多模态大模型看图识字（复用 AI_API_KEY / AI_BASE_URL，无需额外依赖，线上可用）
2. baidu：百度云通用文字识别（免费额度，需配置 AK/SK，识别精度高）
3. paddle：本地 PaddleOCR（离线，需安装 paddlepaddle + paddleocr）
"""
from __future__ import annotations

import base64
import io
import os
import time
from abc import ABC, abstractmethod
from functools import lru_cache

import httpx

# PaddlePaddle 3.x 在 CPU 上 oneDNN 与 PIR 执行器存在兼容问题，
# 需在导入 paddleocr 之前禁用 MKLDNN 默认启用。
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")

from app.config import settings

# 古籍识别限定提示词：只出文字，不翻译、不解释、不补字、不加标点
_VISION_PROMPT = (
    "你是一个古籍文字识别引擎。请逐字识别图片中的全部文字，按原有行序、分行输出。"
    "要求：不翻译、不注释、不补字、不改写、不添加原文没有的标点；"
    "字迹模糊或残缺的字用□代替；如含拼音、注释等小字也一并识别。"
    "只输出识别到的文字本身，不要任何说明或代码块标记。"
)

_BAIDU_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
_BAIDU_OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"


class OCRService(ABC):
    """OCR 服务抽象基类。"""

    name: str = "unknown"

    @abstractmethod
    def recognize(self, image_bytes: bytes) -> str:
        """识别图片中的文字，返回纯文本。"""

    @property
    @abstractmethod
    def available(self) -> bool:
        """服务是否可用。"""


def _guess_mime(image_bytes: bytes) -> str:
    """根据文件头判断图片 MIME，避免依赖 imghdr（Python 3.13 已移除）。"""
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"GIF8"):
        return "image/gif"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    if image_bytes.startswith(b"BM"):
        return "image/bmp"
    return "image/jpeg"


def _strip_code_fence(text: str) -> str:
    """去掉大模型偶尔包裹的 ``` 代码块标记。"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


class VisionOCRService(OCRService):
    """多模态大模型看图识字（豆包 / OpenAI 兼容视觉模型）。"""

    name = "vision"

    def __init__(self) -> None:
        self.api_key = settings.ai_api_key
        self.base_url = settings.ai_base_url.rstrip("/")
        self.model = settings.ai_vision_model
        self.timeout = max(settings.ocr_timeout, settings.ai_timeout)

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.model)

    def recognize(self, image_bytes: bytes) -> str:
        if not self.available:
            raise RuntimeError("未配置 AI_API_KEY / AI_VISION_MODEL，视觉 OCR 不可用")

        mime = _guess_mime(image_bytes)
        b64 = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _VISION_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    ],
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # 兼容部分接口返回分段内容数组
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return _strip_code_fence(content or "")


class BaiduOCRService(OCRService):
    """百度云通用文字识别（需 BAIDU_OCR_API_KEY / BAIDU_OCR_SECRET_KEY）。"""

    name = "baidu"
    _token: str | None = None
    _token_expire_at: float = 0.0

    def __init__(self) -> None:
        self.ak = settings.baidu_ocr_api_key
        self.sk = settings.baidu_ocr_secret_key
        self.timeout = settings.ocr_timeout

    @property
    def available(self) -> bool:
        return bool(self.ak and self.sk)

    def _get_token(self) -> str:
        now = time.time()
        if BaiduOCRService._token and now < BaiduOCRService._token_expire_at:
            return BaiduOCRService._token
        params = {
            "grant_type": "client_credentials",
            "client_id": self.ak,
            "client_secret": self.sk,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(_BAIDU_TOKEN_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(f"百度 OCR 获取 token 失败: {data}")
        BaiduOCRService._token = data["access_token"]
        # 提前 5 分钟过期，避免边界失效
        BaiduOCRService._token_expire_at = now + int(data.get("expires_in", 2592000)) - 300
        return BaiduOCRService._token

    def recognize(self, image_bytes: bytes) -> str:
        if not self.available:
            raise RuntimeError("未配置百度 OCR AK/SK，云 OCR 不可用")

        token = self._get_token()
        form = {
            "image": base64.b64encode(image_bytes).decode("ascii"),
            "language_type": "CHN_ENG",
            "detect_direction": "true",
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                _BAIDU_OCR_URL,
                params={"access_token": token},
                data=form,
            )
            resp.raise_for_status()
            data = resp.json()
        if "error_code" in data:
            raise RuntimeError(f"百度 OCR 识别失败: {data.get('error_msg')}（{data['error_code']}）")
        lines = [item.get("words", "") for item in data.get("words_result", [])]
        return "\n".join(line for line in lines if line)


class PaddleOCRService(OCRService):
    """本地 PaddleOCR 实现（可选依赖）。"""

    name = "paddle"

    def __init__(self) -> None:
        self._ocr = None
        try:
            from paddleocr import PaddleOCR  # type: ignore

            # use_textline_orientation=True 支持方向分类，lang='ch' 中文
            self._ocr = PaddleOCR(use_textline_orientation=True, lang="ch")
        except Exception:
            self._ocr = None

    @property
    def available(self) -> bool:
        return self._ocr is not None

    def recognize(self, image_bytes: bytes) -> str:
        if not self.available:
            raise RuntimeError(
                "PaddleOCR 未安装。请运行 pip install -r requirements-ocr.txt，"
                "或配置视觉大模型 / 百度云 OCR。"
            )
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        result = self._ocr.ocr(np.array(img))
        lines: list[str] = []
        if result and result[0]:
            ocr_result = result[0]
            rec_texts = ocr_result.get("rec_texts") if hasattr(ocr_result, "get") else None
            if rec_texts:
                lines = [t for t in rec_texts if t]
        return "\n".join(lines)


# 自动模式下的优先级：线上可用的云端方案优先，本地 PaddleOCR 兜底
_AUTO_ORDER: tuple[type[OCRService], ...] = (
    VisionOCRService,
    BaiduOCRService,
    PaddleOCRService,
)

_PROVIDER_MAP: dict[str, type[OCRService]] = {
    "vision": VisionOCRService,
    "baidu": BaiduOCRService,
    "paddle": PaddleOCRService,
}


@lru_cache(maxsize=1)
def get_ocr_service() -> OCRService:
    """根据配置返回 OCR 服务实例（进程内缓存，避免重复加载模型）。"""
    provider = settings.ocr_provider.lower().strip()

    if provider in _PROVIDER_MAP:
        return _PROVIDER_MAP[provider]()

    # auto：按优先级返回第一个可用的引擎；全部不可用时返回 vision 实例以便状态展示
    for cls in _AUTO_ORDER:
        service = cls()
        if service.available:
            return service
    return VisionOCRService()
