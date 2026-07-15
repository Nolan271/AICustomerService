# AiCustomerService API 接口文档

> 版本: 1.0 | 更新: 2026-07-15  
> 基础地址: `http://localhost:8001/api/v1`  
> 鉴权方式: `Authorization: Bearer <token>`（外部充电桩平台 Token）

---

## 目录

1. [聊天对话](#1-聊天对话)
2. [历史会话](#2-历史会话)
3. [知识库管理](#3-知识库管理)
4. [数据代理](#4-数据代理)
5. [反馈](#5-反馈)
6. [媒体](#6-媒体)
7. [系统管理](#7-系统管理)
8. [附录：错误码](#8-附录)

---

## 1. 聊天对话

### 1.1 单次问答

发起一次对话请求，AI 根据知识库内容回答。

```
POST /chat/completions
```

**Request Body：**

| 参数 | 类型 | 必填 | 说明 |
|:--|:--|:--:|:--|
| `session_id` | string | ✅ | 会话 ID，相同 ID 延续多轮对话 |
| `message` | string | ✅ | 用户消息，最大 4000 字 |
| `kb_id` | string | ❌ | 知识库 ID（不传则查全部） |
| `user_id` | string | ❌ | 用户标识（匿名时不传） |

**请求示例：**
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "充电桩的保修政策是什么？"
}
```

**Response：**
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "answer": "根据《充电桩售后服务手册》第3章规定，充电桩整机保修期为2年...",
  "sources": [
    {
      "doc_id": "doc-uuid",
      "doc_name": "充电桩售后服务手册.pdf",
      "text": "3.1 保修期限：充电桩整机保修期为2年...",
      "score": 0.92
    }
  ],
  "intent": "KB_QA",
  "need_human_handoff": false,
  "handoff_reason": null,
  "chart_config": null
}
```

**Response 字段说明：**

| 字段 | 类型 | 说明 |
|:--|:--|:--|
| `answer` | string | AI 回答文本（Markdown 格式） |
| `sources` | array | 引用来源列表 |
| `sources[].doc_name` | string | 来源文档名 |
| `sources[].text` | string | 引用片段 |
| `sources[].score` | number | 相关性分数（0-1） |
| `intent` | string | 意图类型：`KB_QA` 知识问答 / `DATA_QUERY` 数据查询 / `CHITCHAT` 闲聊 / `HANDOFF` 转人工 |
| `chart_config` | object | 数据查询时附带的图表配置（ECharts） |
| `fact_count` | number | 当前用户的长期记忆条数 |

---

## 2. 历史会话

### 2.1 获取会话列表

获取当前用户的所有历史对话记录。

```
GET /sessions
```

**Query 参数：**

| 参数 | 类型 | 必填 | 说明 |
|:--|:--|:--:|:--|
| `user_id` | string | ❌ | 按用户筛选（不传则返回全部） |

**Response：**
```json
{
  "items": [
    {
      "id": "a1b2c3d4-...",
      "title": "充电桩保修政策",
      "user_id": "user-123",
      "kb_id": null,
      "status": "active",
      "message_count": 5,
      "created_at": "2026-07-15T10:00:00",
      "updated_at": "2026-07-15T10:05:00"
    }
  ],
  "total": 1
}
```

### 2.2 创建会话

创建一个新会话记录。

```
POST /sessions
```

**Request Body：**

| 参数 | 类型 | 必填 | 说明 |
|:--|:--|:--:|:--|
| `id` | string | ❌ | 不传则自动生成 UUID |
| `title` | string | ❌ | 会话标题，默认"新对话" |
| `user_id` | string | ❌ | 用户标识 |
| `kb_id` | string | ❌ | 关联的知识库 |

### 2.3 获取会话详情

```
GET /sessions/{session_id}
```

### 2.4 删除会话

```
DELETE /sessions/{session_id}
```

### 2.5 获取会话消息

获取某个会话的全部聊天记录。

```
GET /sessions/{session_id}/messages
```

**Response：**
```json
[
  {
    "id": "msg-uuid",
    "conversation_id": "a1b2c3d4-...",
    "role": "user",
    "content": "充电桩的保修政策是什么？",
    "metadata": null,
    "created_at": "2026-07-15T10:00:00"
  },
  {
    "id": "msg-uuid",
    "conversation_id": "a1b2c3d4-...",
    "role": "assistant",
    "content": "根据《充电桩售后服务手册》第3章规定...",
    "metadata": {
      "intent": "KB_QA",
      "sources": [...]
    },
    "created_at": "2026-07-15T10:00:03"
  }
]
```

---

## 3. 知识库管理

### 3.1 获取知识库列表

```
GET /knowledge-bases
```

### 3.2 创建知识库

```
POST /knowledge-bases
```

**Request Body：**
```json
{
  "name": "充电桩产品手册",
  "description": "2024款充电桩产品手册与技术规格"
}
```

### 3.3 获取知识库详情

```
GET /knowledge-bases/{kb_id}
```

### 3.4 更新知识库

```
PUT /knowledge-bases/{kb_id}
```

### 3.5 删除知识库

```
DELETE /knowledge-bases/{kb_id}
```

### 3.6 获取文档列表

```
GET /knowledge-bases/{kb_id}/documents
```

### 3.7 上传文档

上传并自动解析、向量化文档到知识库。

```
POST /knowledge-bases/{kb_id}/documents
```

**请求格式：** `multipart/form-data`

| 参数 | 类型 | 必填 | 说明 |
|:--|:--|:--:|:--|
| `file` | file | ✅ | 支持 PDF / TXT / MD / DOCX / CSV |

**处理流程：** 上传 → 文档解析 → 文本分块 → 向量化 → 存入 Qdrant

### 3.8 删除文档

```
DELETE /knowledge-bases/{kb_id}/documents/{doc_id}
```

---

## 4. 数据代理

转发请求到充电桩外部平台，`Authorization` Token 由前端传递。

### 4.1 通用 GET 代理

```
GET /proxy/{path}
```

代理 `GET` 请求到外部 API，`path` 为外部接口的相对路径。

**请求示例：**
```
GET /api/v1/proxy/home/statUsers
Authorization: Bearer <token>
```

### 4.2 通用 POST 代理

```
POST /proxy/{path}
```

**请求示例：**
```json
POST /api/v1/proxy/home/statRevenue
Authorization: Bearer <token>
Content-Type: application/json

{
  "pageNum": 1,
  "pageSize": 10
}
```

### 可用代理端点列表

| 路径 | 方法 | 说明 |
|:--|:--:|:--|
| `/proxy/home/statRevenue` | POST | 统计营收（今日/本月/今年） |
| `/proxy/home/statOrders` | POST | 统计订单数量 |
| `/proxy/home/statUsers` | POST | 统计用户数量 |
| `/proxy/home/statKwh` | POST | 统计电量 |
| `/proxy/home/statDevStates` | POST | 统计设备状态 |
| `/proxy/stat/statOrdersDays` | POST | 订单趋势（14天/12月） |
| `/proxy/stat/statKwhsDays` | POST | 电量趋势 |
| `/proxy/stat/statUsersDays` | POST | 用户趋势 |
| `/proxy/stat/statRevenueMonthTotal` | POST | 月收入统计 |
| `/proxy/stat/statRevenueDayTotal` | POST | 日收入统计 |

---

## 5. 反馈

### 5.1 提交反馈

```
POST /feedback
```

**Request Body：**
```json
{
  "message_id": "msg-uuid",
  "rating": 5,
  "comment": "回答很准确"
}
```

### 5.2 反馈统计

```
GET /feedback/stats
```

**Response：**
```json
{
  "avg_rating": 4.5,
  "total_count": 100,
  "positive_count": 85
}
```

---

## 6. 媒体

### 6.1 获取文档图片

```
GET /media/images/{image_filename}
```

返回 MinerU 解析出的文档内嵌图片。

---

## 7. 系统管理

### 7.1 健康检查

```
GET /admin/health
```

**Response：**
```json
{
  "status": "ok",
  "app": "AiCustomerService",
  "qdrant": "connected",
  "collections": ["knowledge_base"]
}
```

### 7.2 系统统计

需在请求头携带管理员密钥。

```
GET /admin/stats
Header: X-Admin-Key: admin-secret-key
```

**Response：**
```json
{
  "conversations": 50,
  "messages": 320,
  "feedbacks": 15,
  "avg_rating": 4.2,
  "uptime": 1712345678
}
```

---

## 8. 附录

### 错误码说明

| HTTP 状态码 | 说明 |
|:--|:--|
| `200` | 成功 |
| `201` | 创建成功 |
| `204` | 删除成功（无返回体） |
| `400` | 请求参数错误 |
| `401` | 未授权（Token 无效/已过期） |
| `403` | 无权限（管理员密钥错误） |
| `404` | 资源不存在 |
| `500` | 服务器内部错误 |

### 鉴权说明

所有业务接口（聊天、会话、知识库、代理）需在请求头中携带：
```
Authorization: Bearer <充电桩平台的登录Token>
```

Token 由小程序登录充电桩平台后获得，Python 后端会调充电桩 API 验证 Token 有效性。

管理类接口（`/admin/stats`）使用独立的管理员密钥：
```
X-Admin-Key: admin-secret-key
```

### 流式接口（可选）

```
POST /chat/completions/stream
```

返回 SSE (Server-Sent Events) 流式数据，适用于打字机效果。
