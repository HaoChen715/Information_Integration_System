# syntax=docker/dockerfile:1

# ---- 构建前端静态资源 ----
FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 运行:nginx 托管静态资源并反向代理 /api ----
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY deploy/app/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
