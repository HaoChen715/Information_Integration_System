#!/usr/bin/env bash
# 一键收集诊断信息,生成 tar 包带回外网排错。
set -euo pipefail
cd "$(dirname "$0")"

STAMP=$(date +%Y%m%d-%H%M%S)
WORK="iis-diagnose-${STAMP}"
mkdir -p "$WORK"

echo ">> 收集容器状态与日志"
docker compose ps > "$WORK/ps.txt" 2>&1 || true
docker compose logs --no-color --tail=5000 > "$WORK/app.log" 2>&1 || true
docker version > "$WORK/docker-version.txt" 2>&1 || true
uname -a > "$WORK/system.txt" 2>&1 || true
{ echo "date: $(date)"; echo "pwd: $(pwd)"; ls -la; } > "$WORK/host.txt" 2>&1 || true

echo ">> 复制配置(敏感字段脱敏)"
if [ -f .env ]; then
  sed -E 's/(PASSWORD|SECRET|PASS)[A-Z_]*=.*/\1=***REDACTED***/I' .env > "$WORK/env.redacted" || true
fi

tar czf "${WORK}.tar.gz" "$WORK"
rm -rf "$WORK"

echo ">> 已生成诊断包: $(pwd)/${WORK}.tar.gz"
echo "   请将该文件带回外网用于排错。"
