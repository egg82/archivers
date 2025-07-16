#!/usr/bin/env bash

set -euo pipefail

VERSION=1.3.0
DOCKERFILES=(ubi9-micro ubi9-minimal scratch alpine)
SBOM_DIR=sboms

docker buildx create --use --name sbom-builder >/dev/null 2>&1 || true

mkdir -p "$SBOM_DIR"

for flavor in "${DOCKERFILES[@]}"; do
    IMAGE=egg82/domain_archiver:${flavor}-$VERSION
    DOCKERFILE=Dockerfile-$flavor
    OUT_SBOM="${SBOM_DIR}/${flavor}-${VERSION}.sbom.json"

    docker buildx build --builder sbom-builder --tag "$IMAGE" --sbom true --push -f "$DOCKERFILE" .

    docker buildx imagetools inspect "$IMAGE" --format '{{ json .SBOM }}' > "$OUT_SBOM"
done
