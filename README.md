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
| `SCRAPY_PERSISTENCE_ENABLED` | 是否写入 PostgreSQL / Redis | `false` |
| `PG_HOST` / `PG_PORT` | PostgreSQL 地址与端口 | `192.168.31.201` / `5452` |
| `PG_DATABASE` / `PG_USER` / `PG_PASSWORD` | 数据库、用户、密码 | `admin_db` / `postgres` / 示例密码 |
| `PG_CONNECT_TIMEOUT` | PostgreSQL 连接超时（秒） | `10` |
| `REDIS_URL` | Redis 连接串，用于去重 | `redis://192.168.31.201:6379/0` |
| `REDIS_CONNECT_TIMEOUT` / `REDIS_SOCKET_TIMEOUT` | Redis 连接与读写超时（秒） | `10` |
| `REDIS_DEDUPE_TTL` | 去重键保留时间（秒） | `2592000` |

`SCRAPY_PERSISTENCE_ENABLED=true` 时走数据库写入与 Redis 去重；`false` 时不连接任何外部服务，条目只输出到日志。示例中的密码仅占位，生产环境必须替换。

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

`.env` 中已经预留数据库开关和连接参数：

```dotenv
SCRAPY_PERSISTENCE_ENABLED=false
PG_HOST=192.168.31.201
PG_PORT=5452
PG_DATABASE=admin_db
PG_USER=postgres
PG_PASSWORD=123456
REDIS_URL=redis://192.168.31.201:6379/0
```

目前 `pipelines.py` 仍是空模板，没有任何代码读取这些变量，所以无论开关取值如何，抓取结果都只打印在容器日志里。要让配置真正生效，需要：

1. 在 `pipelines.py` 中实现读取 `SCRAPY_PERSISTENCE_ENABLED` 的 Pipeline；
2. 在 `settings.py` 的 `ITEM_PIPELINES` 注册该 Pipeline；
3. 在 `requirements.txt` 中加入 `psycopg[binary]` 和 `redis`。

Docker 与 Compose 已通过 `env_file` 注入全部变量，届时无需改动部署文件。

## 11. 本地（非 Docker）运行

```bash
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
scrapy list
scrapy crawl <spider_name>
```
