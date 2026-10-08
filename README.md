# Information_Integration_System

信息集成管理系统 — 统一接入多源数据、集中管理业务信息,后期支持 AD 域账号与细粒度权限管控。

## 技术栈

- **后端**:FastAPI + SQLAlchemy 2.0 + Pydantic + JWT,依赖管理使用 **PDM**
- **前端**:Vue3 + Vite + TypeScript + Tailwind CSS + Pinia + Vue Router
- **数据库**:开发阶段 SQLite,后期迁移 PostgreSQL
- **数据源**:Baserow(部署于 `deploy/baserow/`)

## 目录结构

```
├── backend/        # FastAPI 后端
├── frontend/       # Vue3 前端
├── deploy/         # 部署配置(Baserow)
└── docs/           # 设计开发文档
```

## 快速开始

### 后端

```bash
cd backend
pdm install
pdm run python -m scripts.create_user admin admin123 --superuser --full-name 管理员
pdm run dev                 # http://127.0.0.1:8000  (接口文档 /docs)
```

### 前端

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

测试账号:`admin / admin123`

## 文档

详细设计见 [docs/系统设计开发文档.md](docs/系统设计开发文档.md)。
