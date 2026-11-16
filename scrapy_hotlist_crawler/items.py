# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ScrapyHotlistCrawlerItem(scrapy.Item):
    source = scrapy.Field()  # 渠道，例如：中国新闻网
    name = scrapy.Field()  # 单条热榜条目的标题，不是榜单名称
    heat = scrapy.Field()  # 条目原始热度，例如："128.6万"；未提供时可为 None
    tags = scrapy.Field()  # 条目徽标文字，如 ["热"]、["新"]；图标转文字，无徽标用 []
    rank = scrapy.Field()  # 页面展示的排名原样保存，如 "1"、"12"、"置顶"；未展示排名为 None
