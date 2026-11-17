"""古诗文网 (gushiwen.cn) 站点适配器。

古诗文详情页典型结构：
  - 标题：<div class="sons"> 内的 <h1> 或 <b>
  - 作者/朝代：<p class="source"> 内的 <a>
  - 正文：<div class="contson"> 下的文本
"""
from __future__ import annotations

from app.crawler.base import BaseCrawler, SiteAdapter


class GushiwenAdapter(SiteAdapter):
    """古诗文网适配器。"""

    @staticmethod
    def match(url: str) -> bool:
        host = BaseCrawler.site_of(url)
        return any(d in host for d in ("gushiwen.cn", "gushiwen.org", "guwendao.net"))

    def extract(self, url: str, html: str) -> dict:
        soup = BaseCrawler.parse(html)

        # 标题：优先 .sons h1，其次 .sons b，最后 <title>
        title = None
        sons = soup.find("div", class_="sons")
        if sons:
            h1 = sons.find("h1")
            if h1 and h1.get_text(strip=True):
                title = h1.get_text(strip=True)
            else:
                b = sons.find("b")
                if b and b.get_text(strip=True):
                    title = b.get_text(strip=True)
        if not title and soup.title and soup.title.string:
            title = soup.title.string.strip()

        # 作者与朝代：<p class="source"> 内的链接文本
        author = None
        source_p = soup.find("p", class_="source")
        if source_p:
            links = [a.get_text(strip=True) for a in source_p.find_all("a") if a.get_text(strip=True)]
            if links:
                author = " · ".join(links)

        # 正文：<div class="contson"> 下的文本，保留段落换行
        content = None
        contson = soup.find("div", class_="contson")
        if contson:
            paragraphs = []
            for child in contson.children:
                text = None
                if hasattr(child, "name") and child.name == "p":
                    text = child.get_text("\n", strip=True)
                elif hasattr(child, "name") and child.name == "br":
                    text = ""
                elif isinstance(child, str):
                    text = child.strip()
                if text is not None:
                    paragraphs.append(text)
            content = "\n".join(p for p in paragraphs if p).strip()

        # 概述：正文首段或 meta description
        summary = None
        if content:
            summary = content[:200].replace("\n", " ")
        else:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                summary = meta_desc["content"].strip()

        # guwendao.net 已迁移为 SPA，静态 HTML 不含正文；
        # 若专用选择器未取到内容，回退到通用解析保证至少有标题与站点信息。
        if not content:
            fallback = self.fallback_extract(url, html)
            if not title:
                title = fallback["title"]
            if not summary:
                summary = fallback["summary"]

        return {
            "url": url,
            "title": title,
            "summary": summary,
            "content": content,
            "site": "古诗文网",
        }
