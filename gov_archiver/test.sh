#!/usr/bin/env bash

docker build -t gov_archiver:test-micro --file Dockerfile-ubi9-micro .
docker run --rm -e ARCHIVEBOX_URL=https://archive.egg82.me -e API_TOKEN=foo gov_archiver:test-micro

docker build -t gov_archiver:test-minimal --file Dockerfile-ubi9-minimal .
docker run --rm -e ARCHIVEBOX_URL=https://archive.egg82.me -e API_TOKEN=foo gov_archiver:test-minimal

docker build -t gov_archiver:test-scratch --file Dockerfile-scratch .
docker run --rm -e ARCHIVEBOX_URL=https://archive.egg82.me -e API_TOKEN=foo gov_archiver:test-scratch

docker build -t gov_archiver:test-alpine --file Dockerfile-alpine .
docker run --rm -e ARCHIVEBOX_URL=https://archive.egg82.me -e API_TOKEN=foo gov_archiver:test-alpine

# ---

docker network create archiver-net
docker run -d --name redis-test --network archiver-net -e ALLOW_EMPTY_PASSWORD=yes redislabs/rebloom:latest
sleep 8

docker build -t gov_archiver:test-scratch --file Dockerfile-scratch .
docker run --rm --network archiver-net -e ARCHIVEBOX_URL=https://archive.egg82.me -e API_TOKEN=foo -e LOG_LEVEL="debug" -e REDIS_URL="redis://redis-test:6379/0" gov_archiver:test-scratch

docker rm -f redis-test
docker network rm archiver-net
