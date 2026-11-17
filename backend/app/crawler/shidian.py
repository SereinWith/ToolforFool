"""识典古籍 (shidianguji.com) 站点适配器。

内容页典型结构：
  - 书名：<h1>
  - 章节标题：<h2>
  - 正文容器：<article class="chapter-reader">
  - 正文段落：<article> 内的 <p>

书籍详情页（/book/{id}）以章节列表为主，正文较少，使用兜底解析。
"""
from __future__ import annotations

from app.crawler.base import BaseCrawler, SiteAdapter


class ShidianAdapter(SiteAdapter):
    """识典古籍适配器。"""

    @staticmethod
    def match(url: str) -> bool:
        return "shidianguji.com" in BaseCrawler.site_of(url)

    def extract(self, url: str, html: str) -> dict:
        soup = BaseCrawler.parse(html)

        # 标题：章节页取 h2，书籍页取 h1
        title = None
        h2 = soup.find("h2")
        if h2 and h2.get_text(strip=True):
            title = h2.get_text(strip=True)
        else:
            h1 = soup.find("h1")
            if h1 and h1.get_text(strip=True):
                title = h1.get_text(strip=True)

        # 正文：<article class="chapter-reader"> 内的段落
        content = None
        article = soup.find("article", class_="chapter-reader")
        if article:
            paragraphs = [
                p.get_text("\n", strip=True)
                for p in article.find_all("p")
                if p.get_text(strip=True)
            ]
            if paragraphs:
                content = "\n\n".join(paragraphs)

        # 概述：正文首段，否则取书籍简介区域
        summary = None
        if content:
            summary = content[:200].replace("\n", " ")
        else:
            # 书籍详情页：尝试取简介文本
            desc = soup.find(string=lambda s: s and "书籍简介" in s)
            if desc:
                parent = desc.find_parent()
                if parent:
                    summary = parent.get_text(" ", strip=True)[:300]

        return {
            "url": url,
            "title": title,
            "summary": summary,
            "content": content,
            "site": "识典古籍",
        }
