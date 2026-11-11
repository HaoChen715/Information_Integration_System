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
COPY deploy/app/app-locations.conf /etc/nginx/app-locations.conf
COPY deploy/app/nginx-https.conf /etc/nginx/https.conf
COPY deploy/app/enable-tls.sh /docker-entrypoint.d/40-enable-tls.sh
RUN chmod +x /docker-entrypoint.d/40-enable-tls.sh
EXPOSE 80 443
