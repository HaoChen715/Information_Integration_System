#!/bin/sh
set -e

if [ -f /etc/nginx/certs/server.crt ] && [ -f /etc/nginx/certs/server.key ]; then
  cp /etc/nginx/https.conf /etc/nginx/conf.d/https.conf
  echo "TLS enabled: /etc/nginx/certs/server.crt"
else
  rm -f /etc/nginx/conf.d/https.conf
  echo "TLS disabled: no /etc/nginx/certs/server.crt or server.key"
fi
