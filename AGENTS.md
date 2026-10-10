# AGENTS.md — 项目约定(给 AI 助手)

## 项目概览

信息集成管理系统:FastAPI 后端 + Vue3 前端,数据源 Baserow,支持本地账号 / AD 域(LDAP)/ OIDC 统一认证、RBAC 权限与数据范围、Docker 离线部署。

- 后端:`backend/`(FastAPI + SQLAlchemy + PDM)
- 前端:`frontend/`(Vue3 + Vite + TS + Tailwind)
- 部署:`deploy/app/`(Docker 打包)、`deploy/baserow/`、`deploy/test-ad/`、`deploy/test-oidc/`
- 文档:`docs/系统设计开发文档.md`

## 本地开发

- 后端:`cd backend && pdm run dev`(端口 8000,`/docs`)
- 前端:`cd frontend && npm run dev`(端口 5173,已配置 `/api` 代理)
- 测试账号:`admin / admin123`

## 发布流程(每轮功能默认直接执行,无需再确认)

1. **升版本号**(新功能 minor,如 0.7.0 → 0.8.0;修复 patch,如 0.7.0 → 0.7.1)
   同步修改以下位置:
   - `backend/app/main.py` 的 `version="x.y.z"`
   - `deploy/app/docker-compose.yml`、`deploy/app/docker-compose.deploy.yml` 的 `${TAG:-x.y.z}`
   - `deploy/app/.env.example` 的 `TAG=x.y.z`
   - `deploy/app/build-and-save.sh` 的 `TAG=${TAG:-x.y.z}`
   - `deploy/app/README.md` 中的版本引用
2. **构建并导出镜像**:`cd deploy/app && ./build-and-save.sh`(产物 `dist/iis-images-<版本>.tar`)
3. **容器验证**:`cp .env.example .env && docker compose -f docker-compose.deploy.yml up -d`,确认 healthy,再 `down`
4. **打包发布**:生成 `deploy/app/dist/iis-release-<版本>.tar.gz`(镜像 + 部署文件 + 源码快照),删除上一版本产物
5. **提交推送**:`git add -A && git commit && git push origin main`

> `.env`、`*.db`、`dist/`、`data/`、镜像/发布包均在 `.gitignore` 中,不要提交。

## 约定

- 不添加无关注释;遵循现有分层(`api/routes` → `crud` → `models`,`services` 放外部集成)。
- 新增权限点写在 `backend/app/core/permissions.py` 的 `PERMISSION_CATALOG`。
- 数据库变更:无 Alembic,新增列请在 `backend/app/db/migrate.py` 的 `_ADDED_COLUMNS` 登记(SQLite `ALTER TABLE`)。
- 时间字段统一按 UTC 序列化(`app/schemas/common.py::UTCDatetime`)。
- 离线部署:内网无外网,依赖全部封入镜像;升级用 `docker load` + 改 `TAG` + `docker compose up -d`。
