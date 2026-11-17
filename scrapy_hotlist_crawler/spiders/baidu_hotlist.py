"""抓取百度热搜榜（top.baidu.com/board?tab=realtime）的榜单条目。"""

import scrapy

from scrapy_hotlist_crawler.items import ScrapyHotlistCrawlerItem
from scrapy_hotlist_crawler.tags import normalize_tags


class BaiduHotlistSpider(scrapy.Spider):
    name = "baidu_hotlist"
    allowed_domains = ["top.baidu.com"]
    start_urls = ["https://top.baidu.com/board?tab=realtime"]

    # 页面由服务端直出，全部条目都在首屏 HTML 中，无需翻页或调用接口。
    CARD_SELECTOR = 'div[class*="category-wrap_"]'
    RANK_SELECTOR = 'a[class*="img-wrapper_"] div[class*="index_"]'
    TITLE_SELECTOR = 'div[class*="c-single-text-ellipsis"]'
    HEAT_SELECTOR = 'div[class*="hot-index_"]'
    TAG_SELECTOR = 'div[class*="hot-tag_"]'

    # 榜首条目用图标代替序号，百度该图标表示「置顶」。
    PINNED_LABEL = "置顶"

    def parse(self, response):
        seen = set()
        count = 0
        for card in response.css(self.CARD_SELECTOR):
            name = self.clean_text(card.css(f"{self.TITLE_SELECTOR}::text").get())
            if not name or name in seen:
                continue
            seen.add(name)
            count += 1
            yield ScrapyHotlistCrawlerItem(
                source="baidu",
                name=name,
                heat=self.clean_text(card.css(f"{self.HEAT_SELECTOR}::text").get()) or None,
                tags=self.extract_tags(card),
                rank=self.extract_rank(card),
            )

        self.logger.info("百度热搜榜解析到 %d 条", count)

    def extract_rank(self, card):
        """读取页面上展示的排名，不做自行编号。

        - 有数字：直接取该数字（允许跳号，也允许首个不是 1）。
        - 无数字但有图标：取图标 alt；百度用「置顶」图标替代序号。
        - 都没有：返回 None，表示该条不展示排名。
        """
        badge = card.css(self.RANK_SELECTOR)[:1]
        if not badge:
            return None

        text = self.clean_text(badge.xpath("normalize-space(.)").get())
        if text:
            return text

        icons = badge.css("img")
        if not icons:
            return None
        alt = self.clean_text(icons[0].attrib.get("alt"))
        if alt and alt.lower() not in {"true", "false"}:
            return alt
        return self.PINNED_LABEL

    def extract_tags(self, card):
        """把「热」「新」等徽标转成文字列表；非文本徽标读取图片 alt。"""
        raw = card.css(self.TAG_SELECTOR).xpath("string(.)").get() or ""
        tags = [tag for tag in raw.split() if tag]
        if not tags:
            tags = [
                alt.strip()
                for alt in card.css(f"{self.TAG_SELECTOR} img::attr(alt)").getall()
                if alt and alt.strip()
            ]
        return normalize_tags(tags)

    @staticmethod
    def clean_text(value):
        return " ".join((value or "").split())
