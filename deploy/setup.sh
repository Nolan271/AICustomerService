#!/bin/bash
# AiCustomerService 生产环境部署脚本
# 用法: bash deploy/setup.sh
# 前提: 服务器已安装 Docker + Docker Compose

set -e

echo "===== AiCustomerService 生产部署 ====="

# 1. 创建数据目录
echo "[1/5] 创建持久化数据目录..."
mkdir -p /data/sqlite
mkdir -p /data/uploads
mkdir -p /data/media/images
mkdir -p /data/qdrant/storage

# 2. 复制环境配置
echo "[2/5] 配置环境变量..."
if [ ! -f .env.production ]; then
  cp .env.example .env.production
  echo "  ⚠️ 请编辑 .env.production 填入 API Key 等配置"
fi

# 3. 把本地图片同步到数据目录
echo "[3/5] 同步图片资源..."
if [ -d data/media/images ] && [ "$(ls -A data/media/images)" ]; then
  cp -rn data/media/images/* /data/media/images/
  echo "  图片已同步"
else
  echo "  无本地图片，跳过"
fi

# 4. 启动服务
echo "[4/5] 启动 Docker 服务..."
docker compose -f deploy/docker-compose.production.yml --env-file .env.production up -d

# 5. 等待就绪
echo "[5/5] 等待服务就绪..."
for i in {1..12}; do
  sleep 5
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/v1/admin/health 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "  ✅ 服务已就绪！"
    echo ""
    echo "===== 部署完成 ====="
    echo "API:    http://localhost:8001"
    echo "健康检查: http://localhost:8001/api/v1/admin/health"
    echo "Qdrant: localhost:6333"
    echo ""
    echo "数据目录:"
    echo "  SQLite:      /data/sqlite/"
    echo "  上传文件:    /data/uploads/"
    echo "  图片:        /data/media/images/"
    echo "  Qdrant:      /data/qdrant/"
    exit 0
  fi
  echo "  等待中... ($i/12)"
done

echo "  ❌ 服务启动超时，请检查日志: docker logs aics-api"
exit 1
