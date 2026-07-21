# AiCustomerService — API Server Dockerfile
# 多阶段构建: builder → runtime

# ===== Build Stage =====
FROM docker.m.daocloud.io/library/python:3.12-slim AS builder

WORKDIR /app

# 安装 uv（国内可用 pip 安装）
RUN pip install uv -i https://mirrors.aliyun.com/pypi/simple --root-user-action=ignore

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装所有依赖（不含 dev，国内用阿里云源）
RUN uv sync --no-dev --frozen --index-url https://mirrors.aliyun.com/pypi/simple

# 复制源码
COPY app ./app
COPY scripts ./scripts

# ===== Runtime Stage =====
FROM docker.m.daocloud.io/library/python:3.12-slim AS runtime

WORKDIR /app

# 系统依赖（国内用清华源加速）
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    apt-get update && apt-get install -y --no-install-recommends \
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
