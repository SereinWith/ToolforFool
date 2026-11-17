"""爬虫模块。"""
from app.crawler.base import BaseCrawler, SiteAdapter, extract_basic_info
from app.crawler.registry import crawl_and_extract, get_adapter

__all__ = ["BaseCrawler", "SiteAdapter", "extract_basic_info", "crawl_and_extract", "get_adapter"]
