#!/usr/bin/env bash
# 构建前后端镜像并导出为离线 tar 包,供无外网的内网环境使用。
set -euo pipefail
cd "$(dirname "$0")"

TAG=${TAG:-0.9.0}
OUT=${OUT:-dist}
mkdir -p "$OUT"

echo ">> 构建镜像 (tag=${TAG})"
TAG="$TAG" docker compose build

echo ">> 导出离线镜像"
docker save -o "$OUT/iis-images-${TAG}.tar" "iis-backend:${TAG}" "iis-frontend:${TAG}"

echo ">> 完成: ${OUT}/iis-images-${TAG}.tar ($(du -h "$OUT/iis-images-${TAG}.tar" | cut -f1))"
