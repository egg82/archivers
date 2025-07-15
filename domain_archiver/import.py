#!/usr/bin/env python3

from typing import Optional

import os
import sys
import signal
import requests
import re
import time
import json
import gc

import redis

from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
import gzip

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import xml.etree.ElementTree as ET

import logging

import warnings
from bs4 import XMLParsedAsHTMLWarning

TAG=os.environ["TAG"]
ARCHIVEBOX_URL = os.environ["ARCHIVEBOX_URL"].rstrip("/")
API_TOKEN = os.environ["API_TOKEN"]

USER_AGENT = os.environ["USER_AGENT"]
REQUEST_TIMEOUT = int(os.environ["REQUEST_TIMEOUT"])
DEPTH_LIMIT = int(os.environ["DEPTH_LIMIT"])
CRAWL_DELAY = float(os.environ["CRAWL_DELAY"])
SIMULTANEOUS_DOMAINS=int(os.environ["SIMULTANEOUS_DOMAINS"])
THREADS_PER_DOMAIN=int(os.environ["THREADS_PER_DOMAIN"])
raw = os.environ["FOLLOW_ROBOTS"].lower()
FOLLOW_ROBOTS=raw in ("1", "true", "yes")

ARCHIVEBOX_HEADERS = {
  "Authorization": f"Bearer {API_TOKEN}",
  "Content-Type": "application/json",
  "User-Agent": USER_AGENT,
}

ARCHIVEBOX_ADD_BATCH_SIZE = 100

# -- ignore the mess

log_level = os.environ["LOG_LEVEL"].lower()
if log_level == "debug":
  logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
elif log_level == "info":
  logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
elif log_level == "warn" or log_level == "warning":
  logging.basicConfig(level=logging.WARN, format="%(asctime)s [%(levelname)s] %(message)s")
elif log_level == "error":
  logging.basicConfig(level=logging.ERROR, format="%(asctime)s [%(levelname)s] %(message)s")
elif log_level == "critical":
  logging.basicConfig(level=logging.CRITICAL, format="%(asctime)s [%(levelname)s] %(message)s")

DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[A-Za-z]{2,}$"
)

def get_domain(raw: str) -> Optional[str]:
  s = raw.strip()
  if s.startswith(("http://", "https://")):
    parsed = urlparse(s)
    hostname = parsed.hostname
    if not hostname:
      logging.warning(f"Could not extract domain name from URL {s}")
      return None
    domain = hostname
  else:
    domain = s

  domain = domain.lower().rstrip(".")
  if not DOMAIN_RE.fullmatch(domain):
    logging.warning(f"{domain} does not appear to be a valid domain name")
    return None
  return domain

raw = os.environ["DOMAIN_LIST"]
DOMAINS = []
for part in raw.split(";"):
  d = get_domain(part)
  if d:
    DOMAINS.append(d)
if len(DOMAINS) == 0:
  logging.error(f"No valid domains found in DOMAIN_LIST environment variable")
  sys.exit(1)

_default_domain_filters = (
    [rf"^https?://([A-Za-z0-9-]+\.)*{re.escape(domain)}(?::(?:80|443))?(/.*|$)"
     for domain in DOMAINS]
  + [rf"^https?://([A-Za-z0-9-]+\.)*[A-Za-z0-9-]+\.{re.escape(domain)}(?::(?:80|443))?(/.*|$)"
     for domain in DOMAINS]
)

_default_static_filters = [
  r"^https?://([A-Za-z0-9-]+\.)*blob\.core\.windows\.net(/.*|$)",
  r"^https?://([A-Za-z0-9-]+\.)*web\.core\.windows\.net(/.*|$)",
  r"^https?://[A-Za-z0-9-]+\.s3\.amazonaws\.com(/.*|$)",
  r"^https?://s3\.[A-Za-z0-9-]+\.amazonaws\.com/[A-Za-z0-9-]+(/.*|$)",
  r"^https?://[A-Za-z0-9-]+\.s3\.[A-Za-z0-9-]+\.amazonaws\.com(/.*|$)",
  r"^https?://[A-Za-z0-9-]+\.cloudfront\.net(/.*|$)",
  r"^https?://[A-Za-z0-9-]+\.execute-api\.[A-Za-z0-9-]+\.amazonaws\.com(/.*|$)",
  r"^https?://storage\.googleapis\.com/[A-Za-z0-9-]+(/.*|$)",
  r"^https?://[A-Za-z0-9-]+\.storage\.googleapis\.com(/.*|$)",
  r"^https?://[A-Za-z0-9-]+\.appspot\.com(/.*|$)",
  r"^https?://[A-Za-z0-9-]+\.sharepoint\.com(/.*|$)"
]

raw = os.getenv("URL_FILTERS_REGEX", None)
if raw:
  URL_FILTERS = [re.compile(rx) for rx in raw.split(";") if rx.strip()]
else:
  URL_FILTERS = [re.compile(rx) for rx in _default_domain_filters + _default_static_filters]

raw = os.getenv("EXCLUDE_URLS_REGEX", None)
if raw:
  EXCLUDE_URLS_REGEX = re.compile(raw)
else:
  EXCLUDE_URLS_REGEX = re.compile(r"(?i)\.(?:tar(?:\.gz|\.bz2|\.xz)?|css|js|jpe?g|gif|png|bmp|ico|svg|woff2?|ttf|eot|otf|mp3|wav|ogg|mp4|avi|mov|wmv|flv|mkv|zip|rar|bz2|7z|exe|bin|dmg|iso|apk)(?:[?#].*)?$")

raw = os.getenv("NO_CRAWL_URLS_REGEX", None)
if raw:
  NO_CRAWL_URLS_REGEX = re.compile(raw)
else:
  NO_CRAWL_URLS_REGEX = re.compile(r"(?i)\.(?:pdf|xls(?:x|m)?|doc(?:x|m)?|ppt(?:x|m)?|rtf|txt|csv|tsv|md|epub|od[ts]|odp|zip|rar|tar(?:\.gz|\.bz2|\.xz)?|tgz|bz2|7z|exe|bin|dmg|iso|apk|xml|json|rss|atom|ics)(?:[?#].*)?$")

REDIS_URL = os.environ.get("REDIS_URL", None)
REDIS_USER = os.environ.get("REDIS_USER", None)
REDIS_PASS = os.environ.get("REDIS_PASS", None)
REDIS_NAMESPACE = os.environ.get("REDIS_NAMESPACE", "crawler")
MAX_URL_POP = THREADS_PER_DOMAIN * 2

REDIS_QUEUE_KEY = f"{REDIS_NAMESPACE}:queue"
REDIS_BLOOM_KEY = f"{REDIS_NAMESPACE}:bloom"

# -- back to your regularly-scheduled crawler

def get_robots(domain : str, url : Optional[str] = None) -> Optional[RobotFileParser]:
  ret_val = RobotFileParser()

  session = requests.Session()
  session.headers.update({"User-Agent": USER_AGENT})

  for scheme in ("https", "http"):
    try:
      txt = session.get(f"{scheme}://{domain}/robots.txt", timeout=REQUEST_TIMEOUT)
      if txt.status_code == 200:
        ret_val.parse(txt.text.splitlines())
        return ret_val
      
      txt = session.get(f"{scheme}://www.{domain}/robots.txt", timeout=REQUEST_TIMEOUT)
      if txt.status_code == 200:
        ret_val.parse(txt.text.splitlines())
        return ret_val
    except Exception:
      pass

  if url:
    try:
      txt = session.get(f"{url}robots.txt", timeout=REQUEST_TIMEOUT)
      if txt.status_code == 200:
        ret_val.parse(txt.text.splitlines())
        return ret_val
      
      txt = session.get(f"{url}/robots.txt", timeout=REQUEST_TIMEOUT)
      if txt.status_code == 200:
        ret_val.parse(txt.text.splitlines())
        return ret_val
    except Exception:
      pass

  session.close()

  return None

def get_urls_from_sitemaps(robots : Optional[RobotFileParser]) -> list[str]:
  if not robots:
    return []

  sitemap_urls = robots.site_maps()
  if not sitemap_urls or len(sitemap_urls) == 0:
    return []

  ret_val = []

  session = requests.Session()
  session.headers.update({"User-Agent": USER_AGENT})

  for url in sitemap_urls:
    returned_urls = parse_sitemap_urls(url.strip(), session, set())
    for url in returned_urls:
      ret_val.append(url)

  session.close()

  return ret_val

def parse_sitemap_urls(url : str, session : requests.Session, sitemaps : set[str]) -> set[str]:
  if url in sitemaps:
    return set()

  sitemaps.add(url)

  try:
    resp = session.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    data = resp.content
    if url.lower().endswith(".gz") or resp.headers.get("Content-Encoding", "").lower().startswith("gzip"):
      try:
        data = gzip.decompress(data)
      except Exception:
        pass

    root = ET.fromstring(data)
  except Exception as ex:
    logging.error(f"Failed to parse sitemap {url}: {ex}")
    return set()

  urls = set()

  if root.tag.endswith('sitemapindex'):
    for loc in root.findall(".//{*}loc"):
      if loc.text:
        urls.update(parse_sitemap_urls(loc.text.strip(), session, sitemaps))
  elif root.tag.endswith('urlset'):
    for loc in root.findall(".//{*}loc"):
      if loc.text:
        urls.add(loc.text.strip())

  return urls

def get_main_seed_url(domain : str) -> Optional[str]:
  session = requests.Session()
  session.headers.update({"User-Agent": USER_AGENT})

  for scheme in ("https", "http"):
    try:
      res = session.get(f"{scheme}://{domain}/", timeout=REQUEST_TIMEOUT, allow_redirects=True)
      if res.status_code == 200:
        return res.url

      res = session.get(f"{scheme}://www.{domain}/", timeout=REQUEST_TIMEOUT, allow_redirects=True)
      if res.status_code == 200:
        return res.url
    except Exception:
      pass

  session.close()

  return None

def get_links(domain : str, url : str, delay : float, robots : Optional[RobotFileParser], session : requests.Session, redis_conn : Optional[redis.Redis], visited : set[str], lock: threading.Lock, pool : ThreadPoolExecutor, depth : int) -> list[str]:
  if FOLLOW_ROBOTS and robots and not robots.can_fetch(USER_AGENT, url):
    logging.debug(f"Skipping {url} due to robots.txt")
    return []

  if redis_conn:
    if not redis_conn.bf().add(REDIS_BLOOM_KEY, url):
      return []
    if not redis_conn.srem(REDIS_QUEUE_KEY + ":" + domain, url):
      logging.debug(f"Skipping URL {url} due to being already consumed")
      return []
  else:
    with lock:
      if url in visited:
        return []
      visited.add(url)

  ret_val = [url]

  if NO_CRAWL_URLS_REGEX.match(url):
    logging.debug(f"Ending crawl at {url} due to NO_CRAWL_URLS_REGEX")
    return ret_val

  if depth <= 0:
    logging.debug(f"Ending crawl at {url} due to depth limit")
    return ret_val

  time.sleep(delay)

  logging.debug(f"Crawling {url} at depth {depth}")

  try:
    resp = session.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    futures = []
    for a in soup.find_all("a", href=True):
      href = urljoin(resp.url, a["href"]).strip()
      if not href.startswith(("http://","https://")):
        continue

      if redis_conn:
        if redis_conn.bf().exists(REDIS_BLOOM_KEY, url):
          continue
      else:
        with lock:
          if href in visited:
            continue

      if not EXCLUDE_URLS_REGEX.match(href) and any(p.match(href) for p in URL_FILTERS):
        if not redis_conn or redis_conn.sadd(REDIS_QUEUE_KEY + ":" + domain, url):
          futures.append(pool.submit(get_links, domain, href, delay, robots, session, redis_conn, visited, lock, pool, depth - 1))
      for fut in futures:
        ret_val.extend(fut.result())
    soup.decompose()
  except Exception as ex:
    logging.error(f"URL {url} raised exception {ex}")

  return ret_val

def add_urls(urls : list[str]):
  session = requests.Session()
  session.headers.update(ARCHIVEBOX_HEADERS)

  for i in range(0, len(urls), ARCHIVEBOX_ADD_BATCH_SIZE):
    batch = urls[i : i + ARCHIVEBOX_ADD_BATCH_SIZE]
    payload = {"urls": batch, "depth": 0, "tag": TAG}
    try:
      resp = session.post(ARCHIVEBOX_URL + "/api/v1/cli/add", json=payload)
      resp.raise_for_status()
      j = json.loads(resp.text)
      if j["success"] != True:
        logging.error(f"Could not add URL to Archivebox: {json.dumps(j)}")
    except Exception as ex:
      logging.error(f"Could not add URL to Archivebox: {ex}")
    del batch

  session.close()

def crawl_domain(domain : str, redis_conn : Optional[redis.Redis], visited : set[str], lock : threading.Lock) -> tuple[str, int]:
  logging.info(f"Attempting to crawl domain {domain}")

  robots = get_robots(domain)
  main_seed_url = get_main_seed_url(domain)
  if not robots and main_seed_url:
    robots = get_robots(domain, main_seed_url)
  seeds = get_urls_from_sitemaps(robots)
  if main_seed_url:
    seeds.insert(0, main_seed_url)

  if redis_conn and len(seeds) == 0:
    val = redis_conn.srandmember(REDIS_QUEUE_KEY + ":" + domain, MAX_URL_POP)
    if val:
      if isinstance(val, set) or isinstance(val, list):
        for v in val:
          seeds.append(v.decode() if isinstance(v, bytes) else v)
      elif isinstance(val, str) or isinstance(val, bytes):
        seeds.append(val.decode() if isinstance(val, bytes) else val)
      else:
        logging.warning(f"RPOP {REDIS_QUEUE_KEY + ':' + domain} returned invalid data type: {type(val)}")

  if len(seeds) == 0:
    logging.info(f"Skipping domain {domain} due to issues finding starting URL")
    return domain, 0

  logging.info(f"Found valid start URL {seeds[0]}")

  delay = CRAWL_DELAY
  if robots:
    logging.debug(f"Domain {domain} has robots.txt")
    cd = robots.crawl_delay(USER_AGENT)
    if cd:
      try:
        delay = float(cd)
      except Exception as ex:
        logging.warning(f"Could not set crawl delay to {cd}: {ex}")

  logging.debug(f"Using crawl delay of {delay} for domain {domain}")

  session = requests.Session()
  session.headers.update({"User-Agent": USER_AGENT})

  total = 0
  with ThreadPoolExecutor(max_workers=THREADS_PER_DOMAIN) as pool:
    for seed in seeds:
      links = get_links(domain, seed, delay, robots, session, redis_conn, visited, lock, pool, DEPTH_LIMIT)
      links = [x for x in links if x is not None]
      total += len(links)
      add_urls(links)
      del links
  session.close()
  logging.info(f"Crawling for domain {domain} finished")
  return domain, total

def main():
  warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

  lock = threading.Lock()

  i = 0
  num_links = 0

  signal.signal(signal.SIGINT, signal.default_int_handler)

  redis_conn = None
  if REDIS_URL:
    redis_kwargs = {}
    if REDIS_USER and REDIS_PASS:
      redis_kwargs = {"username": REDIS_USER, "password": REDIS_PASS}
    redis_conn = redis.Redis.from_url(REDIS_URL, **redis_kwargs)
    try:
      redis_conn.bf().reserve(REDIS_BLOOM_KEY, 0.01, 10_000_000) # 1% error for ~10M items
      logging.info(f"Conntected to Redis at {REDIS_URL}")
    except Exception as ex:
      logging.error(f"Could not reserve bloom filter in {REDIS_BLOOM_KEY}: {ex}")
      sys.exit(1)

  with ThreadPoolExecutor(max_workers=SIMULTANEOUS_DOMAINS) as pool:
    futures = {pool.submit(crawl_domain, d, redis_conn, set(), lock): d for d in DOMAINS}
    try:
      for fut in as_completed(futures):
        domain, links = fut.result()
        gc.collect()
        num_links += links
        i += 1
        logging.info(f"[{i}/{len(DOMAINS)}] [{num_links} links] Processed {domain} with {links} links")
    except KeyboardInterrupt:
      print("\nInterrupted by user - shutting down...")
      for f in futures:
        f.cancel()
      pool.shutdown(wait=False)
      sys.exit(1)

if __name__ == "__main__":
  main()
