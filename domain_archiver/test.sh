#!/usr/bin/env bash

docker build -t domain_archiver:test-micro --file Dockerfile-ubi9-micro .
docker run --rm -e ARCHIVEBOX_URL=https://archive.egg82.me -e API_TOKEN=foo -e DOMAIN_LIST="example.com;test.com" domain_archiver:test-micro

docker build -t domain_archiver:test-minimal --file Dockerfile-ubi9-minimal .
docker run --rm -e ARCHIVEBOX_URL=https://archive.egg82.me -e API_TOKEN=foo -e DOMAIN_LIST="example.com;test.com" domain_archiver:test-minimal

docker build -t domain_archiver:test-scratch --file Dockerfile-scratch .
docker run --rm -e ARCHIVEBOX_URL=https://archive.egg82.me -e API_TOKEN=foo -e DOMAIN_LIST="example.com;test.com" domain_archiver:test-scratch

docker build -t domain_archiver:test-alpine --file Dockerfile-alpine .
docker run --rm -e ARCHIVEBOX_URL=https://archive.egg82.me -e API_TOKEN=foo -e DOMAIN_LIST="example.com;test.com" domain_archiver:test-alpine
