# 热榜爬虫 Docker 部署

本项目是一个独立的 Scrapy 项目，用于抓取各站点热榜（如「今日热榜」「热搜」「热文」）的条目。部署方式与 `scrapy_news_crawler` 保持一致：

```text
docker compose up -d crawler -> run-scheduled-spiders.sh -> run-all-spiders.sh -> 依次执行全部 Spider
```

容器启动后立即执行一轮全部 Spider，随后在 30 到 90 分钟之间随机等待，再执行下一轮。热点变化快，所以默认间隔比新闻项目（2 到 4 小时）更短，可通过 `.env` 调整。

## 1. 项目结构

```text
scrapy-hotList-crawler/
├── .dockerignore
├── .env.example
├── compose.yaml
├── Dockerfile
├── requirements.txt
├── run-all-spiders.sh
├── run-scheduled-spiders.sh
├── scrapy.cfg
└── scrapy_hotlist_crawler/
    ├── items.py        # 热榜条目字段
    ├── middlewares.py
    ├── pipelines.py    # 预留，当前未启用
    ├── settings.py     # 全局配置：User-Agent、robots、请求头
    └── spiders/
```

## 2. 服务器准备

安装 Docker Engine 与 Compose Plugin，并克隆已发布的仓库：

```bash
cd /opt
git clone https://github.com/duzqiu/scrapy-hotList-crawler.git
cd scrapy-hotList-crawler
```

服务器上的代码只用于放置 `.env` 和 `compose.yaml`；镜像由 Docker 从 GitHub 拉取的提交构建，两者最终一致即可。

## 3. 配置环境变量

```bash
cp .env.example .env
chmod 600 .env
vi .env
```

`.env` 不提交到 Git，Compose 通过 `env_file` 注入容器。常用配置：

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `TZ` | 容器时区 | `Asia/Shanghai` |
| `GIT_REPOSITORY` | 构建时拉取的仓库地址 | `https://github.com/duzqiu/scrapy-hotList-crawler.git` |
| `GIT_REF` | 构建时使用的分支、tag 或 commit | `main` |
| `CRAWL_INTERVAL_MIN_SECONDS` | 每轮最短间隔（秒） | `1800` |
| `CRAWL_INTERVAL_MAX_SECONDS` | 每轮最长间隔（秒） | `5400` |
| `SCRAPY_PERSISTENCE_ENABLED` | 是否写入 PostgreSQL | `false` |
| `PG_HOST` / `PG_PORT` | PostgreSQL 地址与端口 | `192.168.31.201` / `5452` |
| `PG_DATABASE` / `PG_USER` / `PG_PASSWORD` | 数据库、用户、密码 | `admin_db` / `postgres` / 示例密码 |
| `PG_CONNECT_TIMEOUT` | PostgreSQL 连接超时（秒） | `10` |

`SCRAPY_PERSISTENCE_ENABLED=true` 时写入 PostgreSQL；`false` 时不连接数据库，条目只打印到日志。示例中的密码仅占位，生产环境必须替换。

Compose 会把 `GIT_REPOSITORY` 和 `GIT_REF` 拼成远程 Git 构建上下文，Docker 直接从 GitHub 获取 Dockerfile、requirements 和爬虫源码，**不读取服务器上的本地文件**。因此改完代码必须先提交并推送，再执行构建。

生产环境建议把 `GIT_REF` 固定成 tag 或 commit，保证版本可复现。

## 4. 构建并启动

```bash
docker compose build --pull --no-cache crawler
docker compose up -d crawler
```

查看镜像：

```bash
docker image ls scrapy-hotlist-crawler
```

## 5. 查看日志与清理

```bash
docker compose logs -f crawler
docker ps -a --filter name=scrapy-hotlist-crawler
docker image prune
```

容器的 `restart: unless-stopped` 会保持爬虫常驻；如需停止：

```bash
docker compose down
```

## 6. 只运行一轮

临时抓取一次，跑完即退出：

```bash
docker compose run --rm crawler /app/run-all-spiders.sh
```

## 7. 单独调试某个 Spider

```bash
docker compose run --rm --no-deps crawler scrapy crawl <spider_name>
```

## 8. 新增 Spider

把 Spider 文件放到 `scrapy_hotlist_crawler/spiders/`，`scrapy list` 会自动发现，脚本按顺序逐个执行，无需改动 Dockerfile 或 Compose。

当前项目还没有具体站点的 Spider，`run-all-spiders.sh` 在发现 0 个 Spider 时会报错退出，这是预期行为。

## 9. Item 字段

`ScrapyHotlistCrawlerItem` 表示热榜中的一条条目：

| 字段 | 含义 | 示例 |
| --- | --- | --- |
| `source` | 榜单渠道 | `中国新闻网` |
| `name` | 该条热榜的标题 | `泽连斯基再指责SpaceX` |
| `heat` | 条目热度，保留站点原始值，缺失为 `None` | `128.6万` |
| `tags` | 条目徽标文字，如「热」「新」；无徽标为 `[]` | `["热"]` |
| `rank` | 页面展示的排名，原样保留字符串：可跳号、首条可不为 1；图标代替序号时为图标含义；不展示排名为 `None` | `"2"`、`"置顶"` |

## 10. 持久化说明

`pipelines.PostgreSQLPipeline` 已注册为全局 Pipeline，所有 Spider 共用；是否真正落库只看 `.env` 的 `SCRAPY_PERSISTENCE_ENABLED`：

- `false`：不连接 PostgreSQL，条目以 JSON 打印到日志；
- `true`：写入 backend 项目建好的 `article_hot_list_info` 表，去重完全由 SQL 完成。

### 10.1 字段映射

| Item | 表列 | 说明 |
| --- | --- | --- |
| `source` | `source` | 渠道，如 `baidu` |
| `name` | `name` | 条目标题 |
| `heat` | `heat` | 原始热度文本，缺失为 `NULL` |
| `tags` | `tags` | 徽标数组，写入 JSON，缺省 `[]` |
| `rank` | `rank` | 页面展示的排名原样保存，缺失为 `NULL` |

`created_at` / `updated_at` 由 Pipeline 写入 UTC 时间；`is_active` 由 Pipeline 维护，见下一节。

### 10.2 去重、刷新与停用

去重键是 `(source, name)`，数据库上有同名唯一索引 `ux_article_hot_list_info_source_name`，爬虫用一条 upsert 完成「存在则更新、不存在则插入」：

```sql
INSERT INTO article_hot_list_info
    (source, name, heat, tags, rank, is_active, created_at, updated_at)
VALUES (%s, %s, %s, %s::json, %s, TRUE, %s, %s)
ON CONFLICT (source, name) DO UPDATE
SET heat = EXCLUDED.heat,
    tags = EXCLUDED.tags,
    rank = EXCLUDED.rank,
    is_active = TRUE,
    updated_at = EXCLUDED.updated_at;
```

由唯一索引兜底，所以同一渠道下同一标题只会保留一行，重复跑多少轮、甚至多实例并发都不会写出重复数据。

每个 Spider 抓完后，`close_spider` 会把**本轮没再出现**的同渠道条目置为 `is_active = false`：

- 不删除，历史数据保留，后台仍能查看 / 编辑；
- 只影响本轮真正抓到数据的渠道（一条都没抓到的渠道不会误停用）；
- 重新出现在榜单里的条目，下一轮抓取会自动恢复为 `true`。

前台接口 `GET /hot-lists` 与 `/hot-lists/sources` 只返回 / 只统计 `is_active = true` 的条目。

### 10.3 部署前提

目标库需已由 backend 的 `create_all()` 建出 `article_hot_list_info`，并且 `(source, name)` 的唯一索引存在：
它由 backend 启动时的 `sync_missing_indexes()` 自动创建。**先更新并启动 backend，再跑爬虫**，
否则 upsert 会因缺少唯一约束报错。`requirements.txt` 只包含 `psycopg[binary]`，不依赖 Redis。

backend 老库的 `tabs` 废弃列会被启动时的 `sync_dropped_columns()` 直接删除，
`tags` 与 `is_active` 由 `sync_missing_columns()` 补齐，重建镜像重启即可，不需要手工迁移。

## 11. 本地（非 Docker）运行

```bash
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
scrapy list
scrapy crawl <spider_name>
```
