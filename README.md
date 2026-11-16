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

安装 Docker Engine 与 Compose Plugin，把项目放到服务器上：

```bash
cd /opt
# 通过 git clone、上传压缩包或其他方式取得项目
cd /opt/scrapy-hotList-crawler
```

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
| `BUILD_CONTEXT` | 构建上下文，`.` 表示当前代码 | `.` |
| `CRAWL_INTERVAL_MIN_SECONDS` | 每轮最短间隔（秒） | `1800` |
| `CRAWL_INTERVAL_MAX_SECONDS` | 每轮最长间隔（秒） | `5400` |

如果代码已经推到 GitHub，可以把 `BUILD_CONTEXT` 改成远程 Git 上下文，让 Docker 直接拉取指定分支，例如：

```dotenv
BUILD_CONTEXT=https://github.com/<owner>/scrapy-hotList-crawler.git#main
```

生产环境建议把它固定成 tag 或 commit，保证版本可复现。

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

## 10. 持久化说明

当前未启用 Pipeline，抓取结果只打印在容器日志里，也不连接任何数据库。后续接入 PostgreSQL 或 Redis 时：

1. 在 `pipelines.py` 中实现 Pipeline；
2. 在 `settings.py` 的 `ITEM_PIPELINES` 注册；
3. 在 `.env.example` 与 `requirements.txt` 中补充数据库客户端和连接变量。

Docker 和 Compose 配置不需要为此改动。

## 11. 本地（非 Docker）运行

```bash
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
scrapy list
scrapy crawl <spider_name>
```
