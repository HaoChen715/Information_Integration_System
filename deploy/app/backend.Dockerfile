# syntax=docker/dockerfile:1
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PDM_CHECK_UPDATE=false

WORKDIR /app

RUN pip install "pdm>=2.20"

# 先复制依赖清单并安装,充分利用构建缓存
COPY backend/pyproject.toml backend/pdm.lock ./
RUN pdm install --prod --frozen-lockfile

# 再复制业务代码
COPY backend/app ./app
COPY backend/scripts ./scripts

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["pdm", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
