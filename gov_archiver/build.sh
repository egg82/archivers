#!/usr/bin/env bash

VERSION=1.2.0

docker build -t egg82/gov_archiver:ubi9-micro-$VERSION --file Dockerfile-ubi9-micro .
docker push egg82/gov_archiver:ubi9-micro-$VERSION

docker build -t egg82/gov_archiver:ubi9-minimal-$VERSION --file Dockerfile-ubi9-minimal .
docker push egg82/gov_archiver:ubi9-minimal-$VERSION

docker build -t egg82/gov_archiver:scratch-$VERSION --file Dockerfile-scratch .
docker push egg82/gov_archiver:scratch-$VERSION

docker build -t egg82/gov_archiver:alpine-$VERSION --file Dockerfile-alpine .
docker push egg82/gov_archiver:alpine-$VERSION
