"""抓取今日头条「头条热榜」。

数据来自页面自身使用的接口：

    GET https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc

接口一次返回完整榜单（固定 50 条 + 1 条置顶），前端「换一换」只是对同一批数据
按 10 条一组轮转，并没有独立的分页接口，所以这里只请求一次。
"""

import json

import scrapy

from scrapy_hotlist_crawler.items import ScrapyHotlistCrawlerItem
from scrapy_hotlist_crawler.tags import normalize_tags


class ToutiaoHotlistSpider(scrapy.Spider):
    name = "toutiao_hotlist"
    allowed_domains = ["toutiao.com", "www.toutiao.com"]
    start_urls = ["https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"]

    # 置顶条目没有热度，排名也用文字表示。
    PINNED_LABEL = "置顶"

    def parse(self, response):
        try:
            payload = json.loads(response.text)
        except ValueError:
            self.logger.warning(
                "头条热榜接口返回的不是 JSON（可能被风控拦截）：%s %s",
                response.status,
                response.url,
            )
            return

        if payload.get("status") != "success":
            self.logger.warning("头条热榜接口状态异常：%s", payload.get("status"))
            return

        seen = set()
        count = 0

        # 置顶条目是文章链接，字段与普通榜单条目不同（没有 HotValue / LabelDesc）。
        for entry in payload.get("fixed_top_data") or []:
            item = self.build_item(entry, rank=self.PINNED_LABEL, pinned=True)
            if item is None or item["name"] in seen:
                continue
            seen.add(item["name"])
            count += 1
            yield item

        for index, entry in enumerate(payload.get("data") or [], 1):
            item = self.build_item(entry, rank=str(index), pinned=False)
            if item is None or item["name"] in seen:
                continue
            seen.add(item["name"])
            count += 1
            yield item

        self.logger.info("头条热榜解析到 %d 条", count)

    def build_item(self, entry, rank, pinned):
        """把接口条目转成 Item；缺标题的条目直接丢弃。"""
        title = self.clean_text(entry.get("Title"))
        if not title:
            return None

        label = self.clean_text(entry.get("LabelDesc"))
        return ScrapyHotlistCrawlerItem(
            source="toutiao",
            name=title,
            heat=None if pinned else self.clean_text(entry.get("HotValue")) or None,
            tags=normalize_tags([label] if label else []),
            rank=rank,
        )

    @staticmethod
    def clean_text(value):
        return " ".join(str(value or "").split())
