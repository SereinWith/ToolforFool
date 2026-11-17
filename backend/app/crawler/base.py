"""爬虫基类与工具函数（占位实现，后续扩展各站点适配器）。"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings


class BaseCrawler:
    """通用爬虫基类，封装请求与 HTML 解析。"""

    def __init__(self, user_agent: str | None = None, delay: float | None = None) -> None:
        self.user_agent = user_agent or settings.crawler_user_agent
        self.delay = delay if delay is not None else settings.crawler_delay
        # 模拟真实浏览器的完整请求头，降低被反爬拦截的概率
        self._headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        # 重试传输层：对网络错误与 5xx 自动重试最多 3 次
        transport = httpx.HTTPTransport(retries=3)
        self._client = httpx.Client(
            headers=self._headers,
            follow_redirects=True,
            timeout=settings.crawler_timeout,
            transport=transport,
        )

    def fetch(self, url: str) -> str:
        """抓取页面 HTML。"""
        if self.delay > 0:
            time.sleep(self.delay)
        response = self._client.get(url)
        response.raise_for_status()
        return response.text

    @staticmethod
    def parse(html: str) -> BeautifulSoup:
        # 使用内置 html.parser，避免 lxml 在部分环境（如 Python 3.14）编译失败
        return BeautifulSoup(html, "html.parser")

    @staticmethod
    def site_of(url: str) -> str:
        return urlparse(url).netloc

    def close(self) -> None:
        self._client.close()


class SiteAdapter(ABC):
    """站点适配器抽象基类。

    每个具体站点实现 match() 判断是否适配当前 URL，
    并实现 extract() 解析页面结构，返回统一字段。
    """

    @staticmethod
    @abstractmethod
    def match(url: str) -> bool:
        """判断该适配器是否适配给定 URL。"""

    @abstractmethod
    def extract(self, url: str, html: str) -> dict:
        """解析 HTML，返回 {url, title, summary, content, site}。"""

    @staticmethod
    def fallback_extract(url: str, html: str) -> dict:
        """通用兜底解析：适用于未适配的站点。"""
        soup = BaseCrawler.parse(html)
        title = soup.title.string.strip() if soup.title and soup.title.string else None

        summary = None
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            summary = meta_desc["content"].strip()
        else:
            first_p = soup.find("p")
            if first_p and first_p.get_text(strip=True):
                summary = first_p.get_text(strip=True)[:300]

        content = None
        article = soup.find("article") or soup.find("body")
        if article:
            content = article.get_text("\n", strip=True)[:5000]

        return {
            "url": url,
            "title": title,
            "summary": summary,
            "content": content,
            "site": BaseCrawler.site_of(url),
        }


def extract_basic_info(url: str, html: str) -> dict:
    """第一档：提取标题与概述的简易实现（通用兜底）。"""
    return SiteAdapter.fallback_extract(url, html)
