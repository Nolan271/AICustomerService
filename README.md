# AiCustomerService

AI 智能客服问答系统 — 基于 RAG（检索增强生成）的知识库问答解决方案。

## 技术栈

| 层 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| LLM 编排 | LangChain + LangGraph |
| 向量数据库 | Qdrant（混合搜索） |
| 关系数据库 | SQLite (SQLAlchemy) |
| 包管理 | uv |
| 容器化 | Docker Compose |

## 快速启动

### 1. 环境准备

```bash
# 安装 uv（如未安装）
pip install uv

# 进入项目
cd AiCustomerService

# 安装依赖
uv sync
```

### 2. 配置

```bash
# 后端环境配置
cp .env.example .env          # 开发环境
# cp .env.example .env.production  # 生产环境

# 小程序环境配置
cp miniapp/.env.example miniapp/.env                    # 开发环境
# cp miniapp/.env.example miniapp/.env.production        # 生产环境

# 编辑 .env 文件，填入必要配置
# 至少需要配置 OPENAI_API_KEY
```

### 3. 启动基础设施

```bash
# 启动 Qdrant（Docker）
docker compose -f docker/docker-compose.yml up qdrant -d

# 或直接使用 docker run
docker run -d -p 6333:6333 qdrant/qdrant
```

### 4. 初始化

```bash
# 初始化 Qdrant 集合 + 数据库表
uv run python scripts/init_qdrant.py
```

### 5. 启动服务

#### 后端

```bash
# 开发模式（默认 8000 端口）
uv run uvicorn app.main:app --reload --port 8000

# 或指定端口
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001

# 或使用 Docker Compose 全部启动
docker compose -f docker/docker-compose.yml up -d
```

#### 前端（UniApp 小程序 H5 预览）

```bash
cd miniapp
npm install          # 首次需要安装依赖
npm run dev:h5       # H5 模式，浏览器打开 http://localhost:8080
# npm run dev        # 编译到微信小程序，用开发者工具打开 dist/dev/mp-weixin/
```

### 6. 访问

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/api/v1/admin/health
- H5 前端: http://localhost:8080（miniapp 预览）

## 项目结构

```
AiCustomerService/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── api/                 # API 路由层
│   │   ├── v1/              #   - REST API
│   │   └── websocket/       #   - WebSocket 对话
│   ├── core/                # 业务逻辑层
│   ├── workflows/           # LangGraph 工作流
│   │   └── nodes/           #   - 工作流节点
│   ├── rag/                 # RAG 组件
│   ├── models/              # SQLAlchemy ORM 模型
│   ├── schemas/             # Pydantic 模型
│   ├── db/                  # 数据库管理
│   ├── qdrant/              # Qdrant 封装
│   └── llm/                 # LLM 工厂
├── docker/                  # Docker 编排文件
├── scripts/                 # 工具脚本
└── tests/                   # 测试
```

## API 概览

| 分组 | 端点 | 说明 |
|------|------|------|
| 对话 | POST `/api/v1/chat/completions` | 单次问答 |
|      | POST `/api/v1/chat/completions/stream` | 流式问答 (SSE) |
|      | WebSocket `/api/v1/chat/ws` | 实时对话 |
| 会话 | GET/POST `/api/v1/sessions` | 会话 CRUD |
| 知识库 | GET/POST `/api/v1/knowledge-bases` | 知识库管理 |
| 文档 | POST `/api/v1/knowledge-bases/{kb_id}/documents` | 上传文档 |
| 反馈 | POST `/api/v1/feedback` | 提交反馈 |
| 管理 | GET `/api/v1/admin/health` | 健康检查 |

## LangGraph 工作流

```
用户输入 → 意图路由 → 知识检索 → LLM 生成 → 护栏检查 → 记忆持久化 → 响应
```

支持四种意图：`KB_QA`（知识问答）、`CHITCHAT`（闲聊）、`HANDOFF`（转人工）、`CLARIFY`（追问）。
