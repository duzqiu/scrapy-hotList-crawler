"""把热榜条目写入 backend 的 ``article_hot_list_info`` 表。

- 是否写库完全由环境变量 ``SCRAPY_PERSISTENCE_ENABLED`` 控制；
  关闭时不连接 PostgreSQL，只把条目打印到日志。
- 去重由数据库唯一索引 ``(source, name)`` 保证，用一条
  ``INSERT ... ON CONFLICT DO UPDATE`` 完成 upsert，多实例并发也不会重复。
- 一个 Spider 抓完后，本轮没有再次出现的条目会被置为 ``is_active = false``
  （不删除），前台接口只返回启用中的条目。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

from scrapy_hotlist_crawler.tags import normalize_tags

TABLE_NAME = "article_hot_list_info"


def _load_project_env() -> None:
    """Load root .env for direct Scrapy runs; process env wins."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\\\"'"))


_load_project_env()


def is_persistence_enabled() -> bool:
    """Return the global Pipeline switch; default is print-only."""
    value = os.getenv("SCRAPY_PERSISTENCE_ENABLED", "false")
    return value.strip().lower() in {"1", "true", "yes", "on"}


class PostgreSQLPipeline:
    """Persist ``ScrapyHotlistCrawlerItem`` to PostgreSQL."""

    INSERT_SQL = f"""
        INSERT INTO {TABLE_NAME} (
            source, name, heat, tags, rank, is_active, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s::json, %s, TRUE, %s, %s)
        ON CONFLICT (source, name) DO UPDATE
        SET heat = EXCLUDED.heat,
            tags = EXCLUDED.tags,
            rank = EXCLUDED.rank,
            is_active = TRUE,
            updated_at = EXCLUDED.updated_at
    """

    # 本轮没再出现的条目：停用而不是删除，保留历史供后台查看。
    DISABLE_MISSING_SQL = f"""
        UPDATE {TABLE_NAME}
        SET is_active = FALSE, updated_at = %s
        WHERE source = %s AND is_active = TRUE AND name <> ALL(%s::text[])
    """

    def __init__(self) -> None:
        self.pg_conn: psycopg.Connection | None = None
        self.persistence_enabled = is_persistence_enabled()
        # 本轮每个渠道抓到过的标题，close_spider 用来停用「已消失」的条目。
        self.seen: dict[str, set[str]] = {}

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def open_spider(self, spider) -> None:
        if not self.persistence_enabled:
            spider.logger.info("Pipeline disabled: items will only be printed")
            return

        self.pg_conn = psycopg.connect(
            host=os.getenv("PG_HOST", "192.168.31.201"),
            port=int(os.getenv("PG_PORT", "5452")),
            dbname=os.getenv("PG_DATABASE", "admin_db"),
            user=os.getenv("PG_USER", "postgres"),
            password=os.getenv("PG_PASSWORD", "123456"),
            connect_timeout=int(os.getenv("PG_CONNECT_TIMEOUT", "10")),
        )
        spider.logger.info("PostgreSQL connection is ready")

    def close_spider(self, spider) -> None:
        try:
            if self.persistence_enabled and self.pg_conn is not None:
                self._disable_missing(spider)
        finally:
            if self.pg_conn is not None:
                self.pg_conn.close()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if not self.persistence_enabled:
            print(json.dumps(dict(adapter), ensure_ascii=False, indent=2, default=str), flush=True)
            return item

        source = self._text(adapter.get("source"), 50)
        name = self._text(adapter.get("name"), 200)
        if not source or not name:
            raise DropItem("hot list item missing source or name")

        heat = self._text(adapter.get("heat"), 50)
        rank = self._text(adapter.get("rank"), 20)
        tags = normalize_tags(adapter.get("tags"))
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.seen.setdefault(source, set()).add(name)

        try:
            assert self.pg_conn is not None
            with self.pg_conn.cursor() as cursor:
                cursor.execute(
                    self.INSERT_SQL,
                    (source, name, heat, self._json(tags), rank, now, now),
                )
            self.pg_conn.commit()
            return item
        except DropItem:
            raise
        except Exception:
            self.pg_conn.rollback()
            raise

    def _disable_missing(self, spider) -> None:
        """把本轮没再抓到的条目置为禁用；本轮一条都没抓到的渠道跳过。"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            with self.pg_conn.cursor() as cursor:
                disabled = 0
                for source, names in self.seen.items():
                    if not names:
                        continue
                    cursor.execute(
                        self.DISABLE_MISSING_SQL,
                        (now, source, sorted(names)),
                    )
                    disabled += max(cursor.rowcount, 0)
            self.pg_conn.commit()
            spider.logger.info("已停用 %d 条不在本轮榜单中的历史条目", disabled)
        except Exception:
            self.pg_conn.rollback()
            spider.logger.warning("停用历史榜单条目失败", exc_info=True)

    @staticmethod
    def _json(values: list[str]) -> str:
        return json.dumps(values, ensure_ascii=False)

    @staticmethod
    def _text(value: Any, max_length: int) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text[:max_length] or None


# 兼容 Scrapy 模板默认名，避免旧的引用失效。
ScrapyHotlistCrawlerPipeline = PostgreSQLPipeline
