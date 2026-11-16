#!/usr/bin/env bash
set -Eeuo pipefail

# Hot lists change continuously, so the default interval is shorter than the
# news crawler: run immediately, then wait a random 30-90 minutes.
INTERVAL_MIN_SECONDS="${CRAWL_INTERVAL_MIN_SECONDS:-1800}"
INTERVAL_MAX_SECONDS="${CRAWL_INTERVAL_MAX_SECONDS:-5400}"

if ((INTERVAL_MIN_SECONDS < 1 || INTERVAL_MAX_SECONDS < INTERVAL_MIN_SECONDS)); then
  echo "Invalid crawl interval: min=${INTERVAL_MIN_SECONDS} max=${INTERVAL_MAX_SECONDS}" >&2
  exit 1
fi

while true; do
  echo "[$(date -Is)] starting scheduled crawl"
  /app/run-all-spiders.sh
  echo "[$(date -Is)] scheduled crawl finished"

  delay=$((INTERVAL_MIN_SECONDS + RANDOM % (INTERVAL_MAX_SECONDS - INTERVAL_MIN_SECONDS + 1)))
  echo "[$(date -Is)] next crawl in ${delay} seconds"
  sleep "$delay"
done
