#!/bin/bash

set -e

if [ -z "$ARCHIVEBOX_URL" ]; then
  echo "ARCHIVEBOX_URL environment variable missing"
  exit 1
fi

if [ -z "$API_TOKEN" ]; then
  echo "API_TOKEN environment variable missing"
  exit 1
fi

if [ -z "$DOMAIN_LIST" ]; then
  echo "DOMAIN_LIST environment variable missing"
  exit 1
fi

echo "Starting domain_archiver.."

if [ -z "$TAG" ]; then
  export TAG="crawler"
fi

if [ -z "$USER_AGENT" ]; then
  export USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 ArchiveBox/0.8.5 (+https://github.com/ArchiveBox/ArchiveBox/) requests/2.32.4"
fi

if [ -z "$FOLLOW_ROBOTS" ]; then
  export FOLLOW_ROBOTS="1"
fi

if [ -z "$REQUEST_TIMEOUT" ]; then
  export REQUEST_TIMEOUT="10"
fi

if [ -z "$DEPTH_LIMIT" ]; then
  export DEPTH_LIMIT="4"
fi

if [ -z "$CRAWL_DELAY" ]; then
  export CRAWL_DELAY="0.5"
fi

if [ -z "$SIMULTANEOUS_DOMAINS" ]; then
  export SIMULTANEOUS_DOMAINS="3"
fi

if [ -z "$THREADS_PER_DOMAIN" ]; then
  export THREADS_PER_DOMAIN="5"
fi

if [ -z "$LOG_LEVEL" ]; then
  export LOG_LEVEL="info"
fi

export PYTHONPATH=/install/lib/python3.9/site-packages
export PYTHONUNBUFFERED=1

exec python3.9 /app/import.py
