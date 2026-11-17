"""抓取抖音热榜主榜。

页面 https://so-landing.douyin.com/landings/hotlist 是 SPA，数据来自：

    GET https://so-landing.douyin.com/aweme/v1/hot/search/list/
        ?aid=581610&version_code=32.3.0

接口一次返回主榜全部条目（1 条置顶 + 50 条排名），无签名、无 Cookie、无分页；
`data.trending_list`（实时上升热点）不属于主榜，这里不抓。
"""

import json

import scrapy

from scrapy_hotlist_crawler.items import ScrapyHotlistCrawlerItem
from scrapy_hotlist_crawler.tags import normalize_tags


class DouyinHotlistSpider(scrapy.Spider):
    name = "douyin_hotlist"
    allowed_domains = ["so-landing.douyin.com"]
    start_urls = [
        "https://so-landing.douyin.com/aweme/v1/hot/search/list/"
        "?aid=581610&version_code=32.3.0"
    ]

    PINNED_LABEL = "置顶"

    # 接口的 label 是数字编码，文字对照来自页面 bundle。
    LABELS = {
        1: "新",
        2: "商",
        3: "热",
        4: "爆",
        5: "首发",
        6: "直播",
        7: "同城",
        8: "独家",
        9: "挑战",
        10: "当事人",
        16: "辟谣",
        17: "热议",
        202: "上新",
        203: "大促",
        204: "预约",
        205: "代言",
    }

    def parse(self, response):
        try:
            payload = json.loads(response.text)
        except ValueError:
            self.logger.warning(
                "抖音热榜接口返回的不是 JSON：%s %s", response.status, response.url
            )
            return

        if payload.get("status_code") not in (0, None):
            self.logger.warning("抖音热榜接口状态异常：%s", payload.get("status_code"))
            return

        entries = ((payload.get("data") or {}).get("word_list")) or []
        seen = set()
        count = 0

        for entry in entries:
            word = self.clean_text(entry.get("word"))
            if not word or word in seen:
                continue
            seen.add(word)
            count += 1

            position = entry.get("position")
            pinned = entry.get("word_type") == 14 or position is None
            yield ScrapyHotlistCrawlerItem(
                source="douyin",
                name=word,
                heat=None if pinned else self.clean_text(entry.get("hot_value")) or None,
                tags=normalize_tags([self.LABELS.get(entry.get("label"))]),
                rank=self.PINNED_LABEL if pinned else str(position),
            )

        self.logger.info("抖音热榜主榜解析到 %d 条", count)

    @staticmethod
    def clean_text(value):
        return " ".join(str(value if value is not None else "").split())
