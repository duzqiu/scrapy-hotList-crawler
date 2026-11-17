"""抓取新浪热榜主榜（页签「新浪热榜」，tabId=all）。

H5 页面是 SPA，数据来自页面自身调用的接口：

    GET https://newsapp.sina.cn/api/hotlist?newsId=HB-1-snhs/top_news_list

接口一次返回完整主榜（约 45 条），无签名、无 Cookie、无分页参数，
所以这里只请求一次；其它页签（热议 / AI / 娱乐…）不在抓取范围内。
"""

import json

import scrapy

from scrapy_hotlist_crawler.items import ScrapyHotlistCrawlerItem
from scrapy_hotlist_crawler.tags import normalize_tags


class SinaHotlistSpider(scrapy.Spider):
    name = "sina_hotlist"
    allowed_domains = ["newsapp.sina.cn"]
    start_urls = [
        "https://newsapp.sina.cn/api/hotlist?newsId=HB-1-snhs/top_news_list"
    ]

    def parse(self, response):
        try:
            payload = json.loads(response.text)
        except ValueError:
            self.logger.warning(
                "新浪热榜接口返回的不是 JSON：%s %s", response.status, response.url
            )
            return

        if payload.get("status") != 0:
            self.logger.warning("新浪热榜接口状态异常：%s", payload.get("status"))
            return

        entries = ((payload.get("data") or {}).get("hotList")) or []
        seen = set()
        count = 0

        for position, entry in enumerate(entries, 1):
            info = entry.get("info") or {}
            name = self.clean_text(info.get("title"))
            if not name or name in seen:
                # 接口偶发同标题出现两次（不同链接），按标题去重，保留更靠前的一条。
                continue
            seen.add(name)
            count += 1
            yield ScrapyHotlistCrawlerItem(
                source="sina",
                name=name,
                heat=self.clean_text(info.get("hotValue")) or None,
                tags=normalize_tags(info.get("showTag") or []),
                rank=str(position),
            )

        self.logger.info("新浪热榜主榜解析到 %d 条", count)

    @staticmethod
    def clean_text(value):
        return " ".join(str(value or "").split())
