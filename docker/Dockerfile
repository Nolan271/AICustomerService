# AiCustomerService — API Server Dockerfile
# 多阶段构建: builder → runtime

# ===== Build Stage =====
FROM python:3.12-slim AS builder

WORKDIR /app

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装所有依赖（不含 dev）
RUN uv sync --no-dev --frozen

# 复制源码
COPY app ./app
COPY scripts ./scripts

# ===== Runtime Stage =====
FROM python:3.12-slim AS runtime

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制虚拟环境 + 源码
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/scripts /app/scripts

ENV PATH="/app/.venv/bin:$PATH"

# 创建数据目录
RUN mkdir -p /app/data/sqlite /app/data/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/admin/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
