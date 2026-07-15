# AI 客服问答系统 — 完整架构设计

> **技术栈**: Python 3.11+ / FastAPI / LangChain / LangGraph / Qdrant / SQLite / Docker  
> **设计原则**: 模块化、可扩展、生产就绪、领域驱动

---

## 目录

1. [系统概述](#1-系统概述)
2. [架构总览](#2-架构总览)
3. [项目结构](#3-项目结构)
4. [核心组件设计](#4-核心组件设计)
5. [RAG 流水线](#5-rag-流水线)
6. [LangGraph 对话工作流](#6-langgraph-对话工作流)
7. [数据模型与存储](#7-数据模型与存储)
8. [API 设计](#8-api-设计)
9. [Docker 部署](#9-docker-部署)
10. [配置管理](#10-配置管理)
11. [扩展与优化](#11-扩展与优化)

---

## 1. 系统概述

### 1.1 业务目标

基于本地知识库（文档、FAQ、产品手册等），构建具备以下能力的 AI 客服问答系统：

- **语义理解**：基于 RAG 的精准问答，不依赖关键词匹配
- **多轮对话**：保持上下文状态，支持追问与澄清
- **可控可信**：回答基于本地知识库，可溯源至原文片段
- **可管理**：知识库的增删改查、对话日志审计
- **可扩展**：支持多种 LLM 后端、embedding 模型、 reranker

### 1.2 核心能力矩阵

| 能力 | 实现方式 | 关键组件 |
|------|----------|----------|
| 知识库管理 | 文档解析 → 分块 → 向量化 | LangChain Document Loaders / Text Splitters |
| 语义检索 | 向量相似度 + 元数据过滤 | Qdrant + 混合搜索 (dense + sparse) |
| 回答生成 | 检索增强生成 (RAG) | LangChain QA Chain + Prompt Template |
| 多轮对话 | 状态化工作流 | LangGraph StateGraph |
| 溯源引用 | 返回关联文档片段 | RAG 输出携带 source metadata |
| 会话管理 | 持久化对话历史 | SQLite + SQLAlchemy |
| 管理与监控 | Restful API + 管理后台 | FastAPI Admin / 自定义面板 |

---

## 2. 架构总览

### 2.1 分层架构

```
┌──────────────────────────────────────────────────────────────────┐
│                         Presentation Layer                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Web Chat    │  │  Admin UI    │  │  REST API / WebSocket │  │
│  │  (第三方/定制) │  │  (FastAPI)   │  │  (OpenAPI 文档)      │  │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬────────────┘  │
├─────────┼────────────────┼──────────────────────┼────────────────┤
│         ▼                ▼                      ▼                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Application Layer                         │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │  │
│  │  │ Chat Service   │  │ KB Service     │  │ Admin Service│  │  │
│  │  │ (会话管理)      │  │ (知识库管理)    │  │ (系统管理)   │  │  │
│  │  └───────┬────────┘  └───────┬────────┘  └──────┬───────┘  │  │
│  └──────────┼──────────────────┼───────────────────┼───────────┘  │
├─────────────┼──────────────────┼───────────────────┼──────────────┤
│             ▼                  ▼                   ▼              │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   Orchestration Layer                        │  │
│  │  ┌─────────────────────────────────────────────────────┐   │  │
│  │  │           LangGraph 对话工作流                        │   │  │
│  │  │  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐  │   │  │
│  │  │  │  Router  │ │ Retriever│ │  Agent  │ │  Memory│  │   │  │
│  │  │  │  (路由)  │ │ (检索)   │ │ (生成)  │ │ (记忆) │  │   │  │
│  │  │  └─────────┘ └──────────┘ └─────────┘ └────────┘  │   │  │
│  │  └─────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                      RAG Layer                               │  │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐ │  │
│  │  │ Document │ │ Text     │ │ Embedding  │ │ Reranker /   │ │  │
│  │  │ Loaders  │ │ Splitters│ │ Service    │ │ Post-process │ │  │
│  │  └──────────┘ └──────────┘ └───────────┘ └──────────────┘ │  │
│  └────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Data Layer                                 │  │
│  │  ┌──────────────────┐  ┌──────────────────┐                │  │
│  │  │   Qdrant          │  │   SQLite          │                │  │
│  │  │   (向量数据库)     │  │   (关系数据库)     │                │  │
│  │  │   - 文档向量       │  │   - 会话记录       │                │  │
│  │  │   - 元数据索引     │  │   - 知识库元数据   │                │  │
│  │  │   - 混合搜索       │  │   - 用户反馈       │                │  │
│  │  └──────────────────┘  └──────────────────┘                │  │
│  └────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  Infrastructure Layer                        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │ Docker   │ │ Network  │ │ Volume   │ │ Health Check │  │  │
│  │  │ Compose  │ │ Bridge   │ │ Persist  │ │ + Monitoring │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 系统数据流

```
用户提问
    │
    ▼
┌──────────────────┐
│   FastAPI        │  WebSocket / REST
│   Gateway        │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│   LangGraph      │  1. 意图识别 & 路由
│   Workflow       │  2. 对话历史注入 (Memory)
│   (StateGraph)   │  3. 调用 RAG 流水线
└──────┬───────────┘  4. 生成回答 / 追问 / 转人工
       │
       ▼
┌──────────────────┐
│   RAG Pipeline   │
│                  │
│   1. Embed query │───▶ Qdrant 向量检索
│   2. Retrieve    │◀─── 返回 Top-K 片段
│   3. Rerank      │───▶ 精排重排序
│   4. Build prompt│
│   5. LLM 生成    │───▶ 流式输出
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│   后处理          │  引用标注 / 格式化 / 敏感词过滤
│   (Post-process) │
└──────┬───────────┘
       │
       ▼
  返回给用户 (SSE / WebSocket)
```

---

## 3. 项目结构

```
AiCustomerService/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI 应用入口
│   ├── config.py                    # 配置管理（pydantic-settings）
│   ├── dependencies.py              # 依赖注入（DB session, Qdrant client）
│   │
│   ├── api/                         # API 路由层
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py              # 对话相关 API
│   │   │   ├── knowledge_base.py    # 知识库 CRUD API
│   │   │   ├── document.py          # 文档管理 API
│   │   │   ├── session.py           # 会话管理 API
│   │   │   ├── feedback.py          # 用户反馈 API
│   │   │   └── admin.py             # 系统管理 API
│   │   └── websocket/
│   │       └── chat.py              # WebSocket 实时对话
│   │
│   ├── core/                        # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── chat_service.py          # 对话服务
│   │   ├── kb_service.py            # 知识库服务
│   │   ├── document_service.py      # 文档处理服务
│   │   └── embedding_service.py     # embedding 封装
│   │
│   ├── workflows/                   # LangGraph 工作流
│   │   ├── __init__.py
│   │   ├── chat_graph.py            # 对话工作流图定义
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── router_node.py       # 意图路由
│   │   │   ├── retrieval_node.py    # 知识检索
│   │   │   ├── generation_node.py   # 回答生成
│   │   │   ├── memory_node.py       # 记忆管理
│   │   │   └── guardrails_node.py   # 安全护栏
│   │   └── state.py                 # State 定义
│   │
│   ├── rag/                         # RAG 组件
│   │   ├── __init__.py
│   │   ├── loader.py                # 文档加载器
│   │   ├── splitter.py              # 文本分块策略
│   │   ├── embedder.py              # Embedding 封装
│   │   ├── retriever.py             # 检索器（含混合搜索）
│   │   ├── reranker.py              # 重排序
│   │   ├── prompt_templates.py      # Prompt 模板
│   │   └── ingestion.py             # 知识库摄入流水线
│   │
│   ├── models/                      # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── base.py                  # 基类
│   │   ├── knowledge_base.py        # 知识库
│   │   ├── document.py              # 文档
│   │   ├── chunk.py                 # 文档分块
│   │   ├── conversation.py          # 会话
│   │   ├── message.py               # 消息
│   │   └── feedback.py              # 反馈
│   │
│   ├── schemas/                     # Pydantic 模型（API 出入参）
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── knowledge_base.py
│   │   ├── document.py
│   │   ├── session.py
│   │   └── feedback.py
│   │
│   ├── db/                          # 数据库管理
│   │   ├── __init__.py
│   │   ├── session.py               # SQLAlchemy Session
│   │   ├── migrations/              # Alembic 迁移
│   │   │   ├── env.py
│   │   │   ├── alembic.ini
│   │   │   └── versions/
│   │   └── init_db.py               # 数据库初始化
│   │
│   ├── qdrant/                      # Qdrant 客户端封装
│   │   ├── __init__.py
│   │   ├── client.py                # 连接管理
│   │   ├── collection_manager.py    # Collection 管理
│   │   └── search.py                # 检索封装
│   │
│   ├── llm/                         # LLM 封装
│   │   ├── __init__.py
│   │   ├── factory.py               # LLM 工厂（支持多后端）
│   │   ├── openai.py
│   │   ├── ollama.py                # 本地 LLM（Ollama）
│   │   └── callbacks.py             # LangChain Callbacks
│   │
│   └── utils/                       # 工具函数
│       ├── __init__.py
│       └── common.py
│
├── data/                            # 运行时数据卷
│   ├── sqlite/                      # SQLite 数据库文件
│   └── uploads/                     # 文档上传目录
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   ├── test_rag/
│   ├── test_workflows/
│   └── test_services/
│
├── scripts/
│   ├── init_qdrant.py               # 初始化 Qdrant 集合
│   ├── seed_knowledge_base.py       # 初始知识库种子数据
│   └── health_check.py             # 健康检查脚本
│
├── docker/
│   ├── Dockerfile                   # API 服务 Dockerfile
│   ├── Dockerfile.worker            # 后台 Worker Dockerfile
│   └── docker-compose.yml           # 编排文件
│
├── docs/
│   └── api.md                       # API 文档
│
├── .env.example                     # 环境变量模板
├── .gitignore
├── pyproject.toml                   # Python 项目配置
├── poetry.lock / requirements.txt
└── README.md
```

---

## 4. 核心组件设计

### 4.1 配置管理 (`app/config.py`)

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # ---- 应用 ----
    APP_NAME: str = "AI Customer Service"
    DEBUG: bool = False
    SECRET_KEY: str

    # ---- LLM ----
    LLM_PROVIDER: str = "openai"         # openai | ollama | anthropic
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2:7b"

    # ---- Embedding ----
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ---- Qdrant ----
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "knowledge_base"
    QDRANT_VECTOR_SIZE: int = 1536

    # ---- SQLite ----
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/sqlite/app.db"

    # ---- RAG ----
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RETRIEVAL: int = 5
    TOP_K_RERANK: int = 3
    RETRIEVAL_SCORE_THRESHOLD: float = 0.7

    # ---- 对话 ----
    MAX_HISTORY_LENGTH: int = 10       # 保留的对话轮次
    STREAMING: bool = True
    TEMPERATURE: float = 0.3

    # ---- 知识库 ----
    UPLOAD_DIR: str = "./data/uploads"
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".txt", ".md", ".docx", ".csv", ".json"]

    # ---- 管理员 ----
    ADMIN_API_KEY: str

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

### 4.2 LangGraph 对话工作流 (`app/workflows/`)

LangGraph 的 StateGraph 定义了整个对话的状态机。这是整个系统的核心编排层。

```
                        ┌──────────────────┐
                        │   用户输入         │
                        │   (user_input)    │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │   Router Node     │ ← 意图识别
                        │   判断用户意图     │
                        └──┬────┬────┬─────┘
                           │    │    │
               ┌───────────┘    │    └──────────────┐
               ▼                ▼                    ▼
        ┌──────────┐   ┌──────────────┐   ┌────────────────┐
        │ 问答意图   │   │ 闲聊/问候    │   │ 转人工 / 其他   │
        │ (KB_QA)   │   │ (CHITCHAT)  │   │ (HANDOFF)     │
        └─────┬─────┘   └──────┬───────┘   └───────┬────────┘
              │                │                    │
              ▼                ▼                    ▼
        ┌──────────┐   ┌──────────────┐   ┌────────────────┐
        │Retrieval │   │ LLM 直接回应  │   │ 转人工流程      │
        │ Node     │   │ (无检索)      │   │ (记录工单)     │
        └─────┬─────┘   └──────┬───────┘   └───────┬────────┘
              │                │                    │
              ▼                ▼                    ▼
        ┌──────────┐   ┌──────────────┐   ┌────────────────┐
        │Generation│   │ Generation   │   │ 返回转人工通知  │
        │ Node     │   │ Node         │   │                │
        │ (带上下文)│   │ (无上下文)    │   │                │
        └─────┬─────┘   └──────┬───────┘   └───────┬────────┘
              │                │                    │
              └──────┬─────────┘                    │
                     │                              │
                     ▼                              │
        ┌──────────────────┐                        │
        │ Guardrails Node   │◄──────────────────────┘
        │ 安全审核 & 格式    │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │  Memory Node      │ ← 更新对话历史
        │  (持久化)         │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │  最终响应         │
        │  (返回给用户)     │
        └──────────────────┘
```

### 4.3 State 定义 (`app/workflows/state.py`)

```python
import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict

class ChatState(TypedDict):
    """LangGraph 对话状态"""

    # ---- 输入 ----
    session_id: str                              # 会话 ID
    user_input: str                              # 用户当前输入
    user_id: Optional[str]                       # 用户标识
    kb_id: Optional[str]                         # 当前生效的知识库 ID

    # ---- 中间状态 ----
    intent: Optional[str]                        # 识别到的意图
    query_embedding: Optional[list[float]]       # 问题向量
    retrieved_chunks: Optional[list[dict]]       # 检索到的文档分块
    reranked_chunks: Optional[list[dict]]        # 重排序后的分块
    context_documents: Optional[list[str]]       # 组装后的上下文文本

    # ---- 对话历史 ----
    messages: Annotated[list[dict], operator.add]  # 历史消息累加
    history_summary: Optional[str]               # 历史摘要（长对话时）

    # ---- 输出 ----
    answer: Optional[str]                        # 生成的回答
    sources: Optional[list[dict]]                # 引用来源
    follow_up_questions: Optional[list[str]]     # 建议的追问
    need_human_handoff: bool                     # 是否需要转人工
    handoff_reason: Optional[str]                # 转人工原因

    # ---- 元数据 ----
    error: Optional[str]                         # 错误信息
    processing_steps: list[str]                  # 处理步骤记录（调试用）
    latency_ms: Optional[float]                  # 处理耗时
```

---

## 5. RAG 流水线

### 5.1 知识库摄入流水线

```
文档上传
    │
    ▼
┌─────────────────────┐
│  Document Loader    │  支持: PDF / TXT / Markdown / DOCX / CSV / JSON
│  (按文件类型路由)    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Text Splitter      │  策略:
│                     │  - 递归字符分割 (RecursiveCharacterTextSplitter)
│   Chunk Strategy    │  - 语义分割 (SemanticSplitter)
│                     │  - 特殊格式: MarkdownHeaderSplitter
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Embedding          │  生成向量: OpenAI / Ollama / HuggingFace
│  (批量 + 并发)       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Qdrant Upsert      │
│                     │  Payload: chunk_text, doc_id, kb_id,
│  Collection:        │           chunk_index, metadata (page, section, etc.)
│  knowledge_base     │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  SQLite 记录写入     │
│  documents / chunks │  维护元数据与向量库的关联
│  tables             │
└─────────────────────┘
```

**核心代码设计 (`app/rag/ingestion.py`)**:

```python
import asyncio
from typing import Iterator

from langchain_community.document_loaders import (
    PyMuPDFLoader, TextLoader, UnstructuredMarkdownLoader,
    CSVLoader, JSONLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDocument

from app.rag.embedder import EmbeddingService
from app.qdrant.client import QdrantClientWrapper
from app.db.session import AsyncSessionLocal
from app.models.document import Document as DocModel

class IngestionPipeline:
    """知识库摄入流水线 — 异步 + 批次处理 + 进度报告"""

    def __init__(self, embedder: EmbeddingService, qdrant: QdrantClientWrapper):
        self.embedder = embedder
        self.qdrant = qdrant
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

    def _get_loader(self, file_path: str, file_type: str):
        """文件类型路由"""
        loaders = {
            "pdf": lambda: PyMuPDFLoader(file_path),
            "txt": lambda: TextLoader(file_path, encoding="utf-8"),
            "md": lambda: UnstructuredMarkdownLoader(file_path),
            "docx": lambda: ...,
            "csv": lambda: CSVLoader(file_path),
            "json": lambda: JSONLoader(file_path, jq_schema=".[]"),
        }
        loader_fn = loaders.get(file_type)
        if not loader_fn:
            raise ValueError(f"Unsupported file type: {file_type}")
        return loader_fn()

    async def ingest(
        self,
        file_path: str,
        file_type: str,
        kb_id: str,
        doc_id: str,
        metadata: dict | None = None,
    ) -> int:
        """
        摄入单个文档:
        1. 加载 → 2. 分块 → 3. 向量化 → 4. 存入 Qdrant → 5. 写入 SQLite
        返回分块数量
        """
        loader = self._get_loader(file_path, file_type)
        documents: list[LCDocument] = loader.load()

        # 分块
        chunks = self.splitter.split_documents(documents)
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                "doc_id": doc_id,
                "kb_id": kb_id,
                "chunk_index": i,
                **(metadata or {}),
            })

        # 批量向量化 (支持并发)
        BATCH_SIZE = 20
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            texts = [c.page_content for c in batch]
            vectors = await self.embedder.aembed_documents(texts)

            points = [
                {
                    "id": f"{doc_id}_{i + j}",
                    "vector": vectors[j],
                    "payload": {
                        "text": batch[j].page_content,
                        **batch[j].metadata,
                    },
                }
                for j in range(len(batch))
            ]
            await self.qdrant.upsert(points)

        return len(chunks)
```

### 5.2 在线检索流水线

```
用户问题 (query)
    │
    ▼
┌──────────────────┐
│  Embedding        │  query → vector
│  (同步)           │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Qdrant Search    │  向量检索 + 元数据过滤 (kb_id)
│                   │  返回 Top-K = 5
│  Hybrid Search    │  Dense + Sparse (BM25 via Qdrant)
└────────┬─────────┘
         │  原始检索结果 (score, text, metadata)
         ▼
┌──────────────────┐
│  Reranker         │  可选的精排层
│                   │  - Cross-encoder (Cohere / BGE)
│  (可选)           │  - 基于 LLM 的精排
└────────┬─────────┘
         │  重排序后 Top-3
         ▼
┌──────────────────┐
│  Context Builder  │  组装 Prompt 上下文
│                   │  格式: [source1] ... [source2] ...
│  Prompt Assembly  │  注入对话历史 + 检索结果
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  LLM Generation   │  基于上下文生成回答
│                   │  流式输出 (SSE / WebSocket)
│  Streaming        │
└────────┬─────────┘
         │
         ▼
  回答 + 引用来源 + 建议追问
```

**核心代码设计 (`app/rag/retriever.py`)**:

```python
from app.qdrant.search import QdrantSearcher
from app.rag.embedder import EmbeddingService
from app.rag.reranker import RerankerService

class RAGRetriever:
    def __init__(
        self,
        embedder: EmbeddingService,
        qdrant_searcher: QdrantSearcher,
        reranker: RerankerService | None = None,
        top_k: int = 5,
        score_threshold: float = 0.7,
    ):
        self.embedder = embedder
        self.searcher = qdrant_searcher
        self.reranker = reranker
        self.top_k = top_k
        self.score_threshold = score_threshold

    async def retrieve(
        self,
        query: str,
        kb_id: str | None = None,
        filters: dict | None = None,
    ) -> list[dict]:
        """检索流程: embedding → search → optional rerank"""
        # 1. Embedding
        query_vector = await self.embedder.aembed_query(query)

        # 2. Qdrant 检索
        results = await self.searcher.search(
            query_vector=query_vector,
            query_text=query,        # 用于混合搜索的 BM25
            collection="knowledge_base",
            top_k=self.top_k,
            score_threshold=self.score_threshold,
            kb_id=kb_id,
            extra_filters=filters,
        )

        # 3. 可选重排序
        if self.reranker and len(results) > 1:
            results = await self.reranker.rerank(
                query=query,
                documents=[r["payload"]["text"] for r in results],
                top_k=3,
            )

        return results
```

### 5.3 Prompt 模板 (`app/rag/prompt_templates.py`)

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# ---- 主 RAG 问答模板 ----
RAG_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """你是一个专业的客服助手，基于以下知识库内容回答用户的问题。

## 核心原则
1. **只基于提供的知识库内容回答**，不要编造信息
2. 如果知识库内容不足以回答，请诚实地告知用户
3. 引用来源时，标注对应的文档名称和片段
4. 使用友好、专业的语气
5. 回答要简洁但完整

## 上下文知识
{context}

## 对话历史
{chat_history}

## 指令
- 如果用户的问题是日常问候，直接应答
- 如果问题超出知识范围，请说："根据我目前的知识库，我无法准确回答这个问题，建议咨询人工客服。"
- 对于复杂问题，可以先简要总结，再给出详细说明
- 结束时可以给出 1-2 个追问建议""",
    ),
    MessagesPlaceholder(variable_name="messages"),
    ("human", "{input}"),
])

# ---- 意图识别模板 ----
INTENT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """分析用户输入属于以下哪种意图，只返回意图名称（不带其他文字）：
- KB_QA: 询问业务知识、产品信息、服务政策等需要查询知识库的问题
- CHITCHAT: 问候、闲聊、感谢等不需要知识库的通用对话
- HANDOFF: 明确要求转人工、投诉、紧急问题、或涉及个人隐私等问题
- CLARIFY: 需要对上一个回答进行澄清或追问""",
    ),
    ("human", "{input}"),
])

# ---- 回答摘要模板 ----
SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """请将以下对话内容总结为一段简洁的摘要，保留关键信息（用户问题、回答要点、涉及的知识点）。
摘要长度不超过 200 字。""",
    ),
    ("human", "对话内容：\n{dialog}"),
])
```

---

## 6. LangGraph 对话工作流

### 6.1 工作流图定义 (`app/workflows/chat_graph.py`)

```python
from langgraph.graph import StateGraph, END
from app.workflows.state import ChatState
from app.workflows.nodes import (
    router_node,
    retrieval_node,
    generation_node,
    memory_node,
    guardrails_node,
)

def build_chat_graph() -> StateGraph:
    """构建对话工作流图"""

    workflow = StateGraph(ChatState)

    # ---- 注册节点 ----
    workflow.add_node("router", router_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("generation", generation_node)
    workflow.add_node("guardrails", guardrails_node)
    workflow.add_node("memory", memory_node)

    # ---- 设置入口 ----
    workflow.set_entry_point("router")

    # ---- 条件边：根据意图路由 ----
    workflow.add_conditional_edges(
        "router",
        lambda state: state["intent"],
        {
            "KB_QA": "retrieval",
            "CHITCHAT": "generation",     # 闲聊无需检索
            "HANDOFF": "generation",      # 转人工也走生成（返回转人工提示）
            "CLARIFY": "retrieval",       # 追问需要结合上下文检索
        },
    )

    # ---- 固定边 ----
    workflow.add_edge("retrieval", "generation")
    workflow.add_edge("generation", "guardrails")
    workflow.add_edge("guardrails", "memory")
    workflow.add_edge("memory", END)

    return workflow.compile()
```

### 6.2 节点实现示例

**Router Node** (`app/workflows/nodes/router_node.py`):

```python
from langchain_core.prompts import ChatPromptTemplate
from app.llm.factory import LLMFactory
from app.workflows.state import ChatState

INTENT_PROMPT = ChatPromptTemplate.from_template(
    "分析用户输入属于以下哪种意图：KB_QA（知识问答）, CHITCHAT（闲聊问候）, "
    "HANDOFF（转人工）, CLARIFY（追问澄清）。只返回意图名称。\n用户输入: {input}"
)

async def router_node(state: ChatState) -> dict:
    llm = LLMFactory.get_chat_model()
    chain = INTENT_PROMPT | llm
    result = await chain.ainvoke({"input": state["user_input"]})
    intent = result.content.strip().upper()

    valid_intents = {"KB_QA", "CHITCHAT", "HANDOFF", "CLARIFY"}
    if intent not in valid_intents:
        intent = "KB_QA"  # 默认走知识库

    return {
        "intent": intent,
        "processing_steps": [f"意图识别: {intent}"],
    }
```

**Retrieval Node** (`app/workflows/nodes/retrieval_node.py`):

```python
from app.rag.retriever import RAGRetriever
from app.workflows.state import ChatState

async def retrieval_node(state: ChatState) -> dict:
    retriever: RAGRetriever = ...  # 通过依赖注入获取

    results = await retriever.retrieve(
        query=state["user_input"],
        kb_id=state.get("kb_id"),
    )

    contexts = []
    sources = []
    for r in results:
        contexts.append(r["payload"]["text"])
        sources.append({
            "doc_id": r["payload"].get("doc_id"),
            "chunk_id": r["id"],
            "text": r["payload"]["text"][:200],  # 摘要
            "score": r["score"],
            "metadata": {k: v for k, v in r["payload"].items()
                         if k not in ("text",)},
        })

    return {
        "retrieved_chunks": results,
        "context_documents": contexts,
        "sources": sources,
        "processing_steps": [f"检索到 {len(contexts)} 个相关片段"],
    }
```

**Generation Node** (`app/workflows/nodes/generation_node.py`):

```python
from app.rag.prompt_templates import RAG_PROMPT
from app.llm.factory import LLMFactory
from app.workflows.state import ChatState
from app.utils.format_history import format_chat_history

async def generation_node(state: ChatState) -> dict:
    llm = LLMFactory.get_chat_model(temperature=0.3, streaming=True)

    context = "\n\n---\n\n".join([
        f"📄 文档片段 {i+1}:\n{text}"
        for i, text in enumerate(state.get("context_documents", []))
    ]) or "没有找到相关知识库内容。"

    chat_history = format_chat_history(state.get("messages", []))

    chain = RAG_PROMPT | llm

    result = await chain.ainvoke({
        "context": context,
        "chat_history": chat_history,
        "input": state["user_input"],
        "messages": [],  # LangChain MessagePlaceholder
    })

    answer = result.content

    # 生成追问建议
    follow_ups = _generate_follow_ups(answer, state.get("context_documents", []))

    return {
        "answer": answer,
        "follow_up_questions": follow_ups,
        "processing_steps": ["回答生成完成"],
    }

def _generate_follow_ups(answer: str, contexts: list[str]) -> list[str]:
    """简单规则：基于上下文提炼追问建议"""
    if not contexts:
        return []
    # 实际可调用 LLM 生成，这里用占位
    return ["我还能帮你了解其他相关的产品信息吗？"]
```

**Memory Node** (`app/workflows/nodes/memory_node.py`):

```python
from app.workflows.state import ChatState
from app.core.chat_service import save_message_to_db

async def memory_node(state: ChatState) -> dict:
    """持久化对话历史到 SQLite，维护上下文窗口"""

    # 保存用户消息
    await save_message_to_db(
        session_id=state["session_id"],
        role="user",
        content=state["user_input"],
    )

    # 保存助手回复
    await save_message_to_db(
        session_id=state["session_id"],
        role="assistant",
        content=state["answer"],
        metadata={
            "intent": state.get("intent"),
            "sources": state.get("sources"),
            "follow_ups": state.get("follow_up_questions"),
        },
    )

    # 维护历史窗口 — 只保留最近 N 轮
    updated_messages = state.get("messages", [])
    updated_messages.extend([
        {"role": "user", "content": state["user_input"]},
        {"role": "assistant", "content": state["answer"]},
    ])
    max_history = 10
    if len(updated_messages) > max_history * 2:
        updated_messages = updated_messages[-(max_history * 2):]

    return {
        "messages": state.get("messages", []),  # Annotated 会 append
    }
```

### 6.3 工作流调用入口 (`app/core/chat_service.py`)

```python
from app.workflows.chat_graph import build_chat_graph

class ChatService:
    def __init__(self):
        self.graph = build_chat_graph()

    async def chat(self, session_id: str, user_input: str, kb_id: str | None = None):
        """处理单次对话"""

        initial_state = {
            "session_id": session_id,
            "user_input": user_input,
            "kb_id": kb_id,
            "messages": [],         # 从 DB 加载历史
            "processing_steps": [],
        }

        # 从 DB 加载历史消息
        history = await self._load_history(session_id)
        initial_state["messages"] = history

        # 执行工作流
        final_state = await self.graph.ainvoke(initial_state)

        return {
            "answer": final_state["answer"],
            "sources": final_state.get("sources", []),
            "follow_up_questions": final_state.get("follow_up_questions", []),
            "intent": final_state.get("intent"),
            "need_human_handoff": final_state.get("need_human_handoff", False),
        }

    async def chat_stream(self, session_id: str, user_input: str, kb_id: str | None = None):
        """流式对话 — 异步生成器"""
        ...
```

---

## 7. 数据模型与存储

### 7.1 关系模型 (SQLite + SQLAlchemy)

```
┌───────────────────┐       ┌────────────────────┐
│  knowledge_bases   │       │     documents       │
├───────────────────┤       ├────────────────────┤
│ PK id: UUID       │◄──────│ FK kb_id           │
│ name: str         │       │ PK id: UUID        │
│ description: text │       │ filename: str       │
│ created_at: datetime│     │ file_type: str      │
│ updated_at: datetime│     │ file_size: int      │
│ config: JSON       │       │ status: enum       │
│ is_active: bool    │       │   (pending/        │
└───────────────────┘       │    processing/      │
      │                      │    ready/failed)   │
      │                      │ chunk_count: int   │
      │                      │ metadata: JSON     │
      │                      │ created_at         │
      │                      │ updated_at         │
      │                      └────────┬───────────┘
      │                               │
      │                      ┌────────▼───────────┐
      │                      │       chunks        │
      │                      ├────────────────────┤
      │                      │ PK id: UUID        │
      │                      │ FK doc_id          │
      │                      │ chunk_index: int   │
      │                      │ content: text      │
      │                      │ qdrant_point_id: str│
      │                      │ metadata: JSON     │
      │                      │ tokens_approx: int │
      │                      └────────────────────┘
      │
      │     ┌──────────────────────────────┐
      │     │        conversations          │
      │     ├──────────────────────────────┤
      │     │ PK id: UUID                  │
      │     │ user_id: str (optional)      │
      │     │ kb_id: FK (optional)         │
      │     │ title: str                   │
      │     │ status: enum (active/closed) │
      │     │ created_at                   │
      │     │ updated_at                   │
      │     └──────────────┬───────────────┘
      │                    │
      │     ┌──────────────▼───────────────┐
      │     │           messages            │
      │     ├──────────────────────────────┤
      │     │ PK id: UUID                  │
      │     │ FK conversation_id           │
      │     │ role: enum (user/assistant)  │
      │     │ content: text                │
      │     │ metadata: JSON               │
      │     │   - intent                   │
      │     │   - sources[]                │
      │     │   - follow_ups[]             │
      │     │   - tokens_used              │
      │     │   - latency_ms               │
      │     │ created_at                   │
      │     └──────────────────────────────┘
      │
      │     ┌──────────────────────────────┐
      │     │          feedback             │
      │     ├──────────────────────────────┤
      │     │ PK id: UUID                  │
      │     │ FK message_id                │
      │     │ rating: int (1-5)            │
      │     │ comment: text (optional)     │
      │     │ created_at                   │
      │     └──────────────────────────────┘
```

### 7.2 向量模型 (Qdrant)

```
Collection: knowledge_base
├── Vector Config
│   ├── Size: 1536 (text-embedding-3-small)
│   │        or 1024 (bge-large-zh)
│   └── Distance: Cosine
│
├── Payload Index (供过滤)
│   ├── kb_id: Keyword Index
│   ├── doc_id: Keyword Index
│   ├── chunk_index: Integer Index
│   └── metadata.*: 按需建立
│
├── Sparse Vector (混合搜索)
│   └── BM25 关键词检索
│
└── Payload Schema
    ├── text: string          ← 分块文本全文
    ├── kb_id: string         ← 所属知识库
    ├── doc_id: string        ← 所属文档
    ├── chunk_index: int      ← 分块序号
    ├── doc_name: string      ← 文档名（用于展示）
    ├── metadata: object      ← 额外元数据
    │   ├── page: int?        ← PDF 页码
    │   ├── section: string?  ← 章节标题
    │   └── tags: string[]?   ← 标签
    └── created_at: int       ← 摄入时间戳
```

### 7.3 Qdrant 客户端封装 (`app/qdrant/search.py`)

```python
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue,
    SearchRequest, SearchParams,
    NamedVector, NamedSparseVector,
    ScoredPoint,
)

class QdrantSearcher:
    def __init__(self, client: QdrantClient, collection: str):
        self.client = client
        self.collection = collection

    async def search(
        self,
        query_vector: list[float],
        query_text: str | None = None,
        collection: str | None = None,
        top_k: int = 5,
        score_threshold: float = 0.7,
        kb_id: str | None = None,
        extra_filters: dict | None = None,
    ) -> list[ScoredPoint]:
        """混合搜索：稠密向量 + 稀疏关键词"""

        collection = collection or self.collection
        filters = self._build_filter(kb_id, extra_filters)

        search_params = SearchParams(
            hnsw_ef=128,
            exact=False,
        )

        # 构建搜索请求（稠密 + 稀疏混合）
        request = SearchRequest(
            vector=NamedVector(
                name="dense",
                vector=query_vector,
            ),
            filter=filters,
            limit=top_k,
            score_threshold=score_threshold,
            params=search_params,
            with_payload=True,
            with_vector=False,
        )

        # 如果支持稀疏向量，添加 BM25
        if query_text:
            request.sparse_vector = NamedSparseVector(
                name="sparse",
                vector=self._compute_sparse_vector(query_text),
            )

        results = self.client.search_groups(
            collection_name=collection,
            search_request=request,
        )
        return results

    def _build_filter(
        self, kb_id: str | None, extra: dict | None
    ) -> Filter | None:
        """构建 Qdrant 过滤条件"""
        must_conditions = []
        if kb_id:
            must_conditions.append(
                FieldCondition(
                    key="kb_id",
                    match=MatchValue(value=kb_id),
                )
            )
        if extra:
            for key, value in extra.items():
                must_conditions.append(
                    FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=value),
                    )
                )
        return Filter(must=must_conditions) if must_conditions else None
```

---

## 8. API 设计

### 8.1 API 路由总览

| 模块 | 端点 | 方法 | 描述 |
|------|------|------|------|
| **对话** | `/api/v1/chat/completions` | POST | 单次对话（非流式） |
| | `/api/v1/chat/completions/stream` | POST | 流式对话 (SSE) |
| | `/api/v1/chat/ws` | WebSocket | 实时对话 |
| **会话** | `/api/v1/sessions` | GET | 获取会话列表 |
| | `/api/v1/sessions` | POST | 创建新会话 |
| | `/api/v1/sessions/{id}` | GET | 获取会话详情 |
| | `/api/v1/sessions/{id}` | DELETE | 删除会话 |
| | `/api/v1/sessions/{id}/messages` | GET | 获取会话消息历史 |
| **知识库** | `/api/v1/knowledge-bases` | GET | 知识库列表 |
| | `/api/v1/knowledge-bases` | POST | 创建知识库 |
| | `/api/v1/knowledge-bases/{id}` | GET | 知识库详情 |
| | `/api/v1/knowledge-bases/{id}` | PUT | 更新知识库 |
| | `/api/v1/knowledge-bases/{id}` | DELETE | 删除知识库 |
| **文档** | `/api/v1/knowledge-bases/{kb_id}/documents` | GET | 文档列表 |
| | `/api/v1/knowledge-bases/{kb_id}/documents` | POST | 上传文档 |
| | `/api/v1/knowledge-bases/{kb_id}/documents/{id}` | GET | 文档详情 |
| | `/api/v1/knowledge-bases/{kb_id}/documents/{id}` | DELETE | 删除文档 |
| | `/api/v1/knowledge-bases/{kb_id}/documents/{id}/reindex` | POST | 重新索引 |
| **反馈** | `/api/v1/feedback` | POST | 提交反馈 |
| | `/api/v1/feedback/stats` | GET | 反馈统计 |
| **管理** | `/api/v1/admin/health` | GET | 系统健康检查 |
| | `/api/v1/admin/stats` | GET | 系统统计信息 |
| | `/api/v1/admin/clear-cache` | POST | 清除缓存 |

### 8.2 核心 API 实现示例

**对话 API** (`app/api/v1/chat.py`):

```python
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.schemas.chat import ChatRequest, ChatResponse
from app.core.chat_service import ChatService
from app.dependencies import get_chat_service

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/completions", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    """非流式对话：单次问答"""
    result = await chat_service.chat(
        session_id=request.session_id,
        user_input=request.message,
        kb_id=request.kb_id,
    )
    return ChatResponse(
        session_id=request.session_id,
        answer=result["answer"],
        sources=result.get("sources", []),
        follow_up_questions=result.get("follow_up_questions", []),
        intent=result.get("intent"),
        need_human_handoff=result.get("need_human_handoff", False),
    )

@router.post("/completions/stream")
async def chat_completion_stream(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    """流式对话：SSE (Server-Sent Events)"""
    async def event_generator():
        async for chunk in chat_service.chat_stream(
            session_id=request.session_id,
            user_input=request.message,
            kb_id=request.kb_id,
        ):
            yield {"event": "token", "data": chunk}

    return EventSourceResponse(event_generator())
```

**WebSocket 对话** (`app/api/websocket/chat.py`):

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active.pop(session_id, None)

manager = ConnectionManager()

@router.websocket("/chat/ws")
async def websocket_chat(websocket: WebSocket):
    session_id = websocket.query_params.get("session_id")
    if not session_id:
        await websocket.close(code=4000)
        return

    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            user_msg = data.get("message", "")
            kb_id = data.get("kb_id")

            # 流式返回
            async for chunk in chat_service.chat_stream(
                session_id=session_id,
                user_input=user_msg,
                kb_id=kb_id,
            ):
                await websocket.send_json(chunk)

            # 发送结束标记
            await websocket.send_json({"event": "done"})

    except WebSocketDisconnect:
        manager.disconnect(session_id)
```

**知识库管理 API** (`app/api/v1/knowledge_base.py`):

```python
@router.post("/knowledge-bases/{kb_id}/documents", response_model=DocumentResponse)
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    kb_service: KBService = Depends(get_kb_service),
):
    """上传文档到知识库并自动执行摄入流水线"""

    # 验证文件类型
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型: {ext}")

    # 保存文件
    file_path = await kb_service.save_upload(file, kb_id)

    # 异步执行摄入
    doc = await kb_service.ingest_document(
        kb_id=kb_id,
        file_path=file_path,
        file_type=ext.lstrip("."),
        original_filename=file.filename,
    )

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
    )
```

---

## 9. Docker 部署

### 9.1 Docker Compose (`docker/docker-compose.yml`)

```yaml
version: "3.8"

services:
  # ========== API Server ==========
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: ai-cs-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - ../.env
    environment:
      - QDRANT_HOST=qdrant
      - DATABASE_URL=sqlite+aiosqlite:///data/sqlite/app.db
    volumes:
      - sqlite_data:/app/data/sqlite
      - upload_data:/app/data/uploads
    depends_on:
      qdrant:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/admin/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - ai-cs-network

  # ========== Qdrant Vector DB ==========
  qdrant:
    image: qdrant/qdrant:latest
    container_name: ai-cs-qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"   # gRPC / REST API
      - "6334:6334"   # Internal gRPC (集群)
    volumes:
      - qdrant_storage:/qdrant/storage
      - qdrant_snapshots:/qdrant/snapshots
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6333
      - QDRANT__SERVICE__HTTP_PORT=6333
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    networks:
      - ai-cs-network

  # ========== 后台 Worker (知识库摄入) ==========
  worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.worker
    container_name: ai-cs-worker
    restart: unless-stopped
    env_file:
      - ../.env
    environment:
      - QDRANT_HOST=qdrant
      - DATABASE_URL=sqlite+aiosqlite:///data/sqlite/app.db
    volumes:
      - sqlite_data:/app/data/sqlite
      - upload_data:/app/data/uploads
    depends_on:
      qdrant:
        condition: service_healthy
    networks:
      - ai-cs-network

  # ========== (可选) Ollama 本地 LLM ==========
  ollama:
    image: ollama/ollama:latest
    container_name: ai-cs-ollama
    restart: unless-stopped
    profiles:
      - local-llm        # 默认不启动，需指定 profile
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    networks:
      - ai-cs-network

volumes:
  qdrant_storage:
  qdrant_snapshots:
  sqlite_data:
  upload_data:
  ollama_models:

networks:
  ai-cs-network:
    driver: bridge
```

### 9.2 API 服务 Dockerfile (`docker/Dockerfile`)

```dockerfile
# ===== Build Stage =====
FROM python:3.12-slim AS builder

WORKDIR /app

# 安装 Poetry
RUN pip install --no-cache-dir poetry==1.8.3

# 复制依赖文件
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# ===== Runtime Stage =====
FROM python:3.12-slim AS runtime

WORKDIR /app

# 系统依赖（用于 PDF 解析等）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制依赖
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY app /app/app
COPY scripts /app/scripts

# 创建数据目录
RUN mkdir -p /app/data/sqlite /app/data/uploads

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/admin/health || exit 1

# 启动命令（使用 uvicorn）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 9.3 Worker Dockerfile (`docker/Dockerfile.worker`)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖（同 API 服务）
COPY --from=ai-cs-api-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=ai-cs-api-builder /usr/local/bin /usr/local/bin

COPY app /app/app
COPY scripts /app/scripts

RUN mkdir -p /app/data/sqlite /app/data/uploads

# Worker 启动：监听任务队列（可用 Redis/ARQ 或 Celery）
# 这里使用简单的轮询模式
CMD ["python", "-m", "app.worker"]
```

---

## 10. 配置管理

### 10.1 环境变量模板 (`.env.example`)

```bash
# ---- 应用 ----
APP_NAME=AI Customer Service
DEBUG=false
SECRET_KEY=your-secret-key-here

# ---- LLM 配置 ----
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
# OLLAMA_BASE_URL=http://ollama:11434
# OLLAMA_MODEL=qwen2:7b

# ---- Embedding ----
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# ---- Qdrant ----
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=knowledge_base
QDRANT_VECTOR_SIZE=1536

# ---- 数据库 ----
DATABASE_URL=sqlite+aiosqlite:///./data/sqlite/app.db

# ---- RAG 参数 ----
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RETRIEVAL=5
TOP_K_RERANK=3
RETRIEVAL_SCORE_THRESHOLD=0.7

# ---- 对话 ----
MAX_HISTORY_LENGTH=10
STREAMING=true
TEMPERATURE=0.3

# ---- 管理员 ----
ADMIN_API_KEY=admin-secret-key
```

### 10.2 pyproject.toml (`pyproject.toml`)

```toml
[tool.poetry]
name = "AiCustomerService"
version = "0.1.0"
description = "AI 客服问答系统 — 基于 RAG 的智能知识库问答"
authors = ["Your Name"]
readme = "README.md"
packages = [{ include = "app" }]

[tool.poetry.dependencies]
python = ">=3.11,<3.13"
fastapi = "^0.115.0"
uvicorn = { version = "^0.30.0", extras = ["standard"] }
pydantic = "^2.0"
pydantic-settings = "^2.0"
sqlalchemy = "^2.0"
aiosqlite = "^0.20.0"
alembic = "^1.13"
langchain = "^0.3.0"
langchain-community = "^0.3.0"
langchain-openai = "^0.2.0"
langgraph = "^0.2.0"
qdrant-client = "^1.12.0"
sse-starlette = "^2.1.0"
python-multipart = "^0.0.9"
python-magic = "^0.4.27"

# PDF 解析
pypdf = "^5.0"
pdfminer-six = "^20231228"

# DOCX / CSV
python-docx = "^1.1"
# 生产环境建议用 unstructured 替代多个独立 library

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.24"
httpx = "^0.27"
ruff = "^0.6"
mypy = "^1.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.ruff]
line-length = 100
target-version = "py311"
```

---

## 11. 扩展与优化

### 11.1 生产化增强路线

| 阶段 | 优化项 | 方案 |
|------|--------|------|
| **V1** | 完整功能 | 以上设计 + 管理后台 |
| **V2** | 性能优化 | 1) 向量缓存 (LRU Cache) 2) Embedding 批处理并发 3) 连接池调优 |
| **V3** | 混合搜索增强 | 1) Qdrant 稀疏向量 BM25 2) 多路召回融合 3) RAG Fusion |
| **V4** | 高可用 | 1) Qdrant 集群 2) PostgreSQL 替代 SQLite 3) Redis 消息队列 |
| **V5** | 智能增强 | 1) Agent 工具调用 2) 多步推理 3) GraphRAG（知识图谱） |

### 11.2 关键优化策略

**检索优化**：
```python
# 1. 查询扩展 (Query Expansion)
query_variants = await llm.generate(
    f"将以下问题改写成 3 种不同的问法:\n{original_query}"
)

# 2. 多路召回 (Multi-Route Retrieval)
results = await asyncio.gather(
    dense_search(query),
    keyword_search(query),     # BM25 via Qdrant sparse
    summary_search(query),     # Query 摘要匹配
)
# 融合排序 (Reciprocal Rank Fusion)
final = rrf_fusion(results)

# 3. 自适应 Chunk 策略
for doc_type in ["code", "prose", "table"]:
    chunker = get_adaptive_chunker(doc_type)
```

**对话优化**：
```python
# 1. 上下文压缩 (Context Compression)
compressed = await llm.compress(
    f"从以下对话历史提取关键信息:\n{long_history}"
)

# 2. 主动澄清 (Active Clarification)
if ambiguity_score > threshold:
    return {"answer": None, "clarify": "请问您指的是 A 还是 B？"}

# 3. 反馈闭环 (Feedback Loop)
if feedback.rating < 3:
    await auto_improve(conversation_id, feedback)
```

### 11.3 监控与可观测性

- **结构化日志**: structlog / loguru → JSON 格式 → ELK / Loki
- **Metrics**: Prometheus + /metrics 端点 (FastAPI instrumentation)
- **Tracing**: OpenTelemetry 全链路追踪
- **关键指标**:
  - P50/P95/P99 响应延迟
  - 检索召回率 (top-5 包含正确答案)
  - 用户反馈评分趋势
  - Token 消耗统计
  - 知识库摄入吞吐量

---

## 12. 快速启动

```bash
# 1. 克隆并进入项目
cd AiCustomerService

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 3. 使用 Docker Compose 启动全部服务
docker-compose -f docker/docker-compose.yml up -d

# 4. 初始化数据库和 Qdrant 集合
docker-compose exec api python scripts/init_qdrant.py
docker-compose exec api alembic upgrade head

# 5. 导入知识库
# 通过 API 上传文档或执行种子脚本
docker-compose exec api python scripts/seed_knowledge_base.py

# 6. 访问
# API 文档: http://localhost:8000/docs
# Web Chat: http://localhost:8000/chat
```

---

> **文档版本**: v1.0  
> **最后更新**: 2026-07-14  
> **设计者**: AI Architecture Generator
