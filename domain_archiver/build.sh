#!/usr/bin/env bash

set -euo pipefail

VERSION=1.3.0
DOCKERFILES=(ubi9-micro ubi9-minimal scratch alpine)

docker buildx create --use --name sbom-builder || true

for flavor in "${DOCKERFILES[@]}"; do
    IMAGE=egg82/domain_archiver:${flavor}-$VERSION
    DOCKERFILE=Dockerfile-$flavor

    docker buildx build --builder sbom-builder --tag "$IMAGE" --sbom true --push -f "$DOCKERFILE" .
done
