# 信息集成管理系统 — 内网部署手册(Docker 离线镜像)

本目录用于将系统以 **离线 Docker 镜像** 的形式迁移到无外网的内网环境运行。

## 1. 产物说明

| 文件 | 作用 |
| --- | --- |
| `../images/iis-images-<版本>.tar` | 离线镜像包(含后端 `iis-backend` 与前端 `iis-frontend`) |
| `docker-compose.deploy.yml` | 内网部署用 compose(仅使用已加载镜像) |
| `.env.example` | 配置样例,复制为 `.env` 后修改 |
| `diagnose.sh` | 一键收集诊断信息,供带回外网排错 |
| `docker-compose.yml` | 开发/构建用 compose(含 build 段,内网不需使用) |

## 2. 环境要求

- Linux x86_64
- Docker Engine 20.10+ 与 Docker Compose v2(`docker compose` 子命令)
- 无需外网、无需 Python/Node

## 3. 部署步骤

```bash
# ① 加载镜像
docker load -i images/iis-images-0.2.1.tar

# ② 准备配置
cp .env.example .env
vi .env      # 至少修改 SECRET_KEY;按需配置 LDAP 与引导管理员

# ③ 启动
docker compose -f docker-compose.deploy.yml up -d

# ④ 查看状态
docker compose -f docker-compose.deploy.yml ps
```

启动后访问:`http://<服务器IP>:8080`(端口由 `.env` 的 `HTTP_PORT` 控制)。

默认配置下,首次启动会用 `BOOTSTRAP_ADMIN_USERNAME/PASSWORD` 自动创建管理员
(`admin / admin123`),**登录成功后请立即修改密码并清空 `.env` 中的引导配置**。

## 4. 配置说明(`.env`)

| 变量 | 说明 |
| --- | --- |
| `SECRET_KEY` | JWT 签名密钥,**必须改为 ≥32 字节随机字符串** |
| `HTTP_PORT` | 前端对外端口,默认 8080 |
| `TAG` | 镜像版本标签,须与加载的镜像一致 |
| `BOOTSTRAP_ADMIN_*` | 首次启动自动创建的管理员(创建后建议清空) |
| `AUTH_BACKENDS` | 认证后端顺序,如 `["local","ldap"]` |
| `LDAP_ENABLED` | 是否启用 AD 域登录 |
| `LDAP_SERVER` | AD 地址,**生产必须 `ldaps://`** |
| `LDAP_BIND_DN` / `LDAP_BIND_PASSWORD` | 用于搜索的服务账号 |
| `LDAP_BASE_DN` | 域根,如 `DC=corp,DC=com` |
| `LDAP_GROUP_ROLE_MAP` | AD 组 → 本地角色映射,JSON 格式 |

生成随机密钥示例:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 5. 常用运维命令

```bash
C="docker compose -f docker-compose.deploy.yml"

$C ps                 # 状态
$C logs -f backend    # 后端日志
$C logs -f frontend   # 前端日志
$C restart backend    # 重启后端(改配置后)
$C down               # 停止(保留数据卷)
$C down -v            # 停止并删除数据(慎用)
```

数据(SQLite)保存在 Docker 卷 `iis_backend_data` 中,`down` 不会丢失。

## 6. 出现问题时:生成诊断包

```bash
./diagnose.sh
```

会生成 `iis-diagnose-<时间>.tar.gz`,内含容器日志、状态、系统信息与**脱敏后**的 `.env`。
请将该文件带回外网,即可定位问题。

## 7. 版本升级

```bash
docker load -i images/iis-images-<新版本>.tar
# 修改 .env 中的 TAG=<新版本>
docker compose -f docker-compose.deploy.yml up -d
```

## 8. 手动创建/管理用户(可选)

```bash
docker compose -f docker-compose.deploy.yml exec backend \
  pdm run python -m scripts.create_user <用户名> <密码> --superuser
```

## 9. 安全提醒

- `.env` 含密钥,请勿外泄或提交到代码仓库。
- 生产环境务必:修改 `SECRET_KEY`、启用 HTTPS、AD 使用 `ldaps://`。
- 当前对外协议为 HTTP,建议在内网前置反向代理或网关做 TLS 卸载。
