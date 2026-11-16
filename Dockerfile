# Compose uses the published GitHub repository as the build context, so Docker
# fetches the committed source directly and no Git client is needed in the image.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/requirements.txt

COPY scrapy.cfg /app/scrapy.cfg
COPY scrapy_hotlist_crawler /app/scrapy_hotlist_crawler
COPY run-all-spiders.sh /app/run-all-spiders.sh
COPY run-scheduled-spiders.sh /app/run-scheduled-spiders.sh
RUN chmod +x /app/run-all-spiders.sh /app/run-scheduled-spiders.sh

CMD ["/app/run-scheduled-spiders.sh"]
