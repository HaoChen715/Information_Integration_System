# TLS 证书目录

把内网 CA 签发的证书放到本目录即可自动启用 HTTPS(无需改 compose):

- `server.crt`:服务器证书(建议包含完整链:服务器证书 + 内网 CA)
- `server.key`:服务器私钥(不要提交到仓库,已在 `.gitignore` 排除)

占位后重启前端即可:

```bash
docker compose -f docker-compose.deploy.yml up -d frontend
```

证书的 SAN 必须包含实际访问的域名(如需 `https://IP` 访问,还要加 IP SAN)。
系统会同时保留 `http://<IP>:8080`,方便未配置 DNS/证书信任前继续用 IP 测试。

## 测试用自签证书(可选)

没有现成证书时,可生成一套本地 CA + 服务器证书临时验证:

```bash
./gen-selfsigned.sh iis.corp.local 192.168.31.253
```

生成 `ca.crt / ca.key` 与 `server.crt / server.key`。
把 `ca.crt` 安装到客户端"受信任的根证书颁发机构"后,浏览器访问域名不再告警。
生产请替换为内网 CA 正式签发的证书。
