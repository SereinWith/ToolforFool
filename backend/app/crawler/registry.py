"""站点适配器注册表：按 URL 域名自动选择对应解析器。"""
from __future__ import annotations

from app.crawler.base import BaseCrawler, SiteAdapter
from app.crawler.gushiwen import GushiwenAdapter
from app.crawler.shidian import ShidianAdapter

# 已注册的站点适配器（按优先级排列）
ADAPTERS: list[type[SiteAdapter]] = [
    GushiwenAdapter,
    ShidianAdapter,
]


def get_adapter(url: str) -> SiteAdapter:
    """根据 URL 返回匹配的站点适配器，未匹配则返回通用兜底。"""
    for adapter_cls in ADAPTERS:
        if adapter_cls.match(url):
            return adapter_cls()
    # 未匹配到专用适配器时，使用兜底
    return _FallbackAdapter()


class _FallbackAdapter(SiteAdapter):
    """通用兜底适配器。"""

    @staticmethod
    def match(url: str) -> bool:
        return True

    def extract(self, url: str, html: str) -> dict:
        return self.fallback_extract(url, html)


def crawl_and_extract(url: str) -> dict:
    """抓取 URL 并按站点适配器解析，返回统一字段字典。"""
    crawler = BaseCrawler()
    try:
        html = crawler.fetch(url)
    finally:
        crawler.close()
    adapter = get_adapter(url)
    return adapter.extract(url, html)
