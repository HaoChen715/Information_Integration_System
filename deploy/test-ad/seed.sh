#!/usr/bin/env bash
# 向测试 AD 中播种用户与组,便于联调。
# 用法: ./seed.sh [用户名] [密码] [组名]
set -euo pipefail

CONTAINER=${CONTAINER:-test-samba-ad}
USER_NAME=${1:-zhangsan}
USER_PASS=${2:-User@12345}
GROUP=${3:-iis-admins}

echo ">> 创建用户 ${USER_NAME}"
docker exec "$CONTAINER" samba-tool user create "$USER_NAME" "$USER_PASS" \
  --use-username-as-cn \
  --given-name="$USER_NAME" \
  --mail-address="${USER_NAME}@example.local" || true

echo ">> 创建组 ${GROUP}"
docker exec "$CONTAINER" samba-tool group add "$GROUP" || true

echo ">> 将 ${USER_NAME} 加入 ${GROUP}"
docker exec "$CONTAINER" samba-tool group addmembers "$GROUP" "$USER_NAME" || true

echo "完成。组 DN 通常为: CN=${GROUP},CN=Users,DC=example,DC=local"
