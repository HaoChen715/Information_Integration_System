#!/usr/bin/env bash
# 构建前后端镜像并导出为离线 tar 包,供无外网的内网环境使用。
set -euo pipefail
cd "$(dirname "$0")"

TAG=${TAG:-0.23.2}
POSTGRES_IMAGE=${POSTGRES_IMAGE:-postgres:16-alpine}
OUT=${OUT:-dist}
mkdir -p "$OUT"

echo ">> 构建镜像 (tag=${TAG})"
TAG="$TAG" docker compose build

echo ">> 准备数据库镜像 ${POSTGRES_IMAGE}"
docker image inspect "$POSTGRES_IMAGE" >/dev/null 2>&1 || docker pull "$POSTGRES_IMAGE"

echo ">> 导出离线镜像"
docker save -o "$OUT/iis-images-${TAG}.tar" "iis-backend:${TAG}" "iis-frontend:${TAG}" "$POSTGRES_IMAGE"

echo ">> 完成: ${OUT}/iis-images-${TAG}.tar ($(du -h "$OUT/iis-images-${TAG}.tar" | cut -f1))"
