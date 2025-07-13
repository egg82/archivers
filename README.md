# Archivers

> Crawlers that scrape URLs from domains and submit them to [ArchiveBox](https://github.com/ArchiveBox/ArchiveBox).

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)  
domain_archiver [![Docker Pulls (domain_archiver)](https://img.shields.io/docker/pulls/egg82/domain_archiver)](https://hub.docker.com/r/egg82/domain_archiver)  
gov_archiver [![Docker Pulls (gov_archiver)](https://img.shields.io/docker/pulls/egg82/gov_archiver)](https://hub.docker.com/r/egg82/gov_archiver)

---

## Table of Contents

- [Features](#features)  
- [Getting Started](#getting-started)  
  - [Prerequisites](#prerequisites)  
  - [Installation](#installation)  
- [Usage](#usage)  
  - [Domain Archiver](#domain-archiver)  
  - [Gov Archiver](#gov-archiver)  
- [Configuration](#configuration)  
- [Docker](#docker)  
- [Contributing](#contributing)  
- [License](#license)  

---

## Features

- **Parallel** crawling of multiple domains.  
- Respects `robots.txt` (optional).  
- Parses sitemaps (XML) for seed URLs.  
- Filters out unwanted domains or URLs.  
- Submits discovered URLs in bulk to ArchiveBox (v0.8.0+) via its REST API.  

---

## Getting Started

### Prerequisites

- **Python** ≥ 3.8  
- **pip**  
- (optional) **Docker** & **docker-compose**  
- ArchiveBox v0.8.0 or higher (features REST API)

### Installation

```bash
# Clone the repo
git clone https://github.com/egg82/archivers.git
cd archivers

# Install the domain-archiver
cd domain_archiver
python3 -m pip install -r requirements.txt

# .. or install the gov-archiver
cd ../gov_archiver
python3 -m pip install -r requirements.txt
```

---

## Usage

All options are passed in via environment variables.

### Domain Archiver

```bash
export ARCHIVEBOX_URL="https://archivebox.example.com"
export API_TOKEN="your_api_token"
export DOMAIN_LIST="example.com;test.com"
export TAG="archivebox-tag"

# tuning
export DEPTH_LIMIT=1
export CRAWL_DELAY=0.5
export SIMULTANEOUS_DOMAINS=3
export THREADS_PER_DOMAIN=8
export FOLLOW_ROBOTS=true
export LOG_LEVEL=info

# optional: customize which URLs to include
# export URL_FILTERS_REGEX="^https?://([A-Za-z0-9-]+\.)*example\.com(/.*)?$"

python3 import.py
```

### Gov Archiver

```bash
export ARCHIVEBOX_URL="https://archivebox.example.com"
export API_TOKEN="your_api_token"
export TAG="gov-run-$(date +%Y%m%d)"
export DEPTH_LIMIT=0
export CRAWL_DELAY=0.2
export SIMULTANEOUS_DOMAINS=5
export THREADS_PER_DOMAIN=4
export FOLLOW_ROBOTS=true
export LOG_LEVEL=info

python3 import.py
```

---

## Configuration

| Variable                          | Description                                                                                                     |
|-----------------------------------|-----------------------------------------------------------------------------------------------------------------|
| `ARCHIVEBOX_URL`                  | Base URL of your ArchiveBox instance (no trailing slash).                                                       |
| `API_TOKEN`                       | Bearer token for the ArchiveBox REST API.                                                                       |
| `TAG`                             | Tag to apply to all submitted URLs.                                                                             |
| `DOMAIN_LIST` (domain_archiver)   | Semicolon-separated list of domains to crawl.                                                                   |
| `FOLLOW_ROBOTS`                   | `1`/`true`/`yes`/`0`/`false`/`no` - whether to obey `robots.txt`.                                               |
| `URL_FILTERS_REGEX`               | (Optional) Semicolon-separated regexes to override default URL filters.                                         |
| `EXCLUDE_URLS_REGEX`              | (Optional) Regex to override default exclude URLs. (default: skips archiving various file extensions)           |
| `NO_CRAWL_URLS_REGEX`             | (Optional) Regex to override default no-crawl URLs. (default: skips crawling various file extensions)           |
| `DOMAIN_TYPE_NEGATIVE_FILTER_REGEX` (gov_archiver) | Regex to exclude certain “Domain type” values when fetching the `.gov` list.                   |
| `DEPTH_LIMIT`                     | How many link-hops from each seed URLs (0 = just the seeds).                                                    |
| `CRAWL_DELAY`                     | Seconds to wait between requests to the same site.                                                              |
| `SIMULTANEOUS_DOMAINS`            | Number of domains to crawl in parallel.                                                                         |
| `THREADS_PER_DOMAIN`              | Threads per domain for recursive crawling.                                                                      |
| `REQUEST_TIMEOUT`                 | HTTP timeout (seconds) for all requests.                                                                        |
| `USER_AGENT`                      | User-agent string to present when fetching pages or robots.txt.                                                 |
| `LOG_LEVEL`                       | `debug`, `info`, `warn`, `error`, or `critical`.                                                                |

---

## Docker

You can also run either archiver via Docker Hub images:

```bash
# Domain Archiver
docker run --rm \
  -e ARCHIVEBOX_URL="https://archivebox.example.com" -e API_TOKEN="your_api_token" -e DOMAIN_LIST="example.com;test.com" \
  egg82/domain_archiver:1.0.1-alpine

# Gov Archiver
docker run --rm \
  -e ARCHIVEBOX_URL="https://archivebox.example.com" -e API_TOKEN="your_api_token" \
  egg82/gov_archiver:1.0.1-alpine
```

If you want to build locally:

```bash
cd domain_archiver
docker build -t domain_archiver-local --file Dockerfile-alpine .

cd ../gov_archiver
docker build -t gov_archiver-local --file Dockerfile-alpine .
```

---

## Contributing

1. Fork the repo  
2. Create a feature branch  
3. Submit a pull request  

Please open an issue first for major changes or feature requests.

---

## License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) for details.
