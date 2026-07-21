# AiCustomerService 生产部署指南

## 目录结构

```
服务器:
├── /home/deploy/AiCustomerService/     ← 项目代码（git pull）
│   ├── deploy/
│   │   ├── docker-compose.production.yml
│   │   ├── nginx.conf
│   │   ├── setup.sh
│   │   └── README.md
│   ├── .env.production                  ← 生产环境配置
│   └── ...（其余源码）
│
├── /data/                               ← 持久化数据
│   ├── sqlite/app.db                    ← 对话记录
│   ├── uploads/                         ← 上传文件
│   ├── media/images/                    ← 知识库图片
│   └── qdrant/storage/                  ← 向量数据库
```

## 首次部署

```bash
# 1. 服务器上安装 Docker
curl -fsSL https://get.docker.com | sh

# 2. 上传项目到服务器
scp -r AiCustomerService root@你的IP:/home/deploy/

# 3. 进入项目目录
cd /home/deploy/AiCustomerService

# 4. 配置环境变量
cp .env.example .env.production
# 编辑 .env.production，填入:
#   - OPENAI_API_KEY / DASHSCOPE_API_KEY
#   - EXTERNAL_API_BASE_URL
#   - WECHAT_TOKEN

# 5. 一键部署
bash deploy/setup.sh
```

## 日常管理

```bash
# 查看状态
docker ps | grep aics

# 查看日志
docker logs aics-api -f
docker logs aics-qdrant -f

# 重启
docker compose -f deploy/docker-compose.production.yml restart api

# 更新代码
cd /home/deploy/AiCustomerService
git pull
docker compose -f deploy/docker-compose.production.yml build --no-cache api
docker compose -f deploy/docker-compose.production.yml up -d api

# 完全停止
docker compose -f deploy/docker-compose.production.yml down
```

## 数据备份

```bash
# 备份全部数据
tar -czf /backup/aics-data-$(date +%Y%m%d).tar.gz /data/

# 恢复
tar -xzf /backup/aics-data-20260717.tar.gz -C /
```
