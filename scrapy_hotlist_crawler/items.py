# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ScrapyHotlistCrawlerItem(scrapy.Item):
    source = scrapy.Field()  # 渠道，例如：中国新闻网
    name = scrapy.Field()  # 单条热榜条目的标题，不是榜单名称
    heat = scrapy.Field()  # 条目原始热度，例如："128.6万"；未提供时可为 None
    tags = scrapy.Field()  # 「热」/「新」统一归一，其它标签（辟谣、解读等）保留原文
    rank = scrapy.Field()  # 页面展示的排名原样保存，如 "1"、"12"、"置顶"；未展示排名为 None
