"""AI 大模型服务抽象层（阶段三）。

支持豆包（火山引擎）与 OpenAI 兼容接口。
未配置 API Key 时，相关接口返回降级结果或提示配置。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.config import settings


class LLMService(ABC):
    """大模型服务抽象基类。"""

    @abstractmethod
    def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        """发送对话消息，返回模型回复文本。"""

    @property
    @abstractmethod
    def available(self) -> bool:
        """服务是否可用（已配置 API Key）。"""


class DoubaoProvider(LLMService):
    """豆包（火山引擎 Ark）实现。"""

    def __init__(self) -> None:
        self.api_key = settings.ai_api_key
        self.base_url = settings.ai_base_url.rstrip("/")
        self.model = settings.ai_model
        self.timeout = settings.ai_timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        if not self.available:
            raise RuntimeError("未配置 AI_API_KEY，无法调用大模型服务")
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


class OpenAIProvider(LLMService):
    """OpenAI 兼容接口实现。"""

    def __init__(self) -> None:
        self.api_key = settings.ai_api_key
        self.base_url = settings.ai_base_url.rstrip("/")
        self.model = settings.ai_model
        self.timeout = settings.ai_timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        if not self.available:
            raise RuntimeError("未配置 AI_API_KEY，无法调用大模型服务")
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


def get_llm_service() -> LLMService:
    """根据配置返回对应的大模型服务实例。"""
    provider = settings.ai_provider.lower()
    if provider == "openai":
        return OpenAIProvider()
    return DoubaoProvider()


# ===== 业务能力封装 =====

# 内置简易同义词典，用于无 AI Key 时的降级关键词扩展
_FALLBACK_SYNONYMS: dict[str, list[str]] = {
    "黄帝": ["轩辕", "轩辕氏", "有熊氏"],
    "炎帝": ["神农氏", "烈山氏"],
    "孔子": ["孔丘", "仲尼", "孔夫子"],
    "李白": ["李太白", "青莲居士", "诗仙"],
    "杜甫": ["杜子美", "少陵野老", "诗圣"],
    "苏轼": ["苏东坡", "苏子瞻", "东坡居士"],
    "司马迁": ["太史公", "子长"],
}


def expand_keywords(query: str, llm: LLMService | None = None) -> list[str]:
    """语义关键词扩展：将用户查询扩展为多个检索关键词。

    优先调用大模型生成同义词/近义词/相关词；
    若大模型不可用，则使用内置同义词典降级。
    """
    query = query.strip()
    if not query:
        return []

    keywords = {query}

    # 尝试大模型扩展
    if llm and llm.available:
        try:
            prompt = (
                f"你是一个古籍研究助手。请将用户查询扩展为 3-8 个用于检索古籍的关键词，"
                f"包括同义词、近义词、别称、相关人物/地名。只输出关键词，用逗号分隔，不要解释。\n"
                f"查询：{query}"
            )
            resp = llm.chat(
                [
                    {"role": "system", "content": "你是一个古籍研究助手，擅长古文词汇扩展。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            for kw in resp.replace("，", ",").split(","):
                kw = kw.strip().strip("。.、；;")
                if kw:
                    keywords.add(kw)
        except Exception:
            pass  # 大模型调用失败，降级

    # 内置同义词典降级
    for key, syns in _FALLBACK_SYNONYMS.items():
        if key in query or query in key:
            keywords.update(syns)

    return list(keywords)


def summarize_text(text: str, llm: LLMService | None = None, max_length: int = 200) -> str:
    """AI 内容摘要。大模型不可用时返回文本前 max_length 字。"""
    if not text:
        return ""
    if llm and llm.available:
        try:
            prompt = f"请用不超过 {max_length} 字概括以下古籍内容：\n\n{text[:3000]}"
            return llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
            )
        except Exception:
            pass
    return text[:max_length].replace("\n", " ")
