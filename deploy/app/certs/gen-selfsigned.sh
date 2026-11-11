#!/usr/bin/env bash
# 生成测试用自签 CA 与服务器证书(可被浏览器信任,前提是客户端信任 ca.crt)
set -euo pipefail
cd "$(dirname "$0")"

DOMAIN=${1:-iis.corp.local}
IP=${2:-192.168.31.253}

openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -out ca.crt -subj "/CN=IIS Internal CA"

openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=${DOMAIN}"

cat > server.ext <<EOF
subjectAltName=DNS:${DOMAIN},DNS:localhost,IP:${IP},IP:127.0.0.1
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EOF

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -sha256 -extfile server.ext

rm -f server.csr server.ext
echo "已生成:server.crt / server.key / ca.crt / ca.key"
echo "请把 ca.crt 安装到客户端受信任根证书后访问 https://${DOMAIN}"
