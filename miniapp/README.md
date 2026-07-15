# AI 智能客服 — UniApp 小程序

## 集成步骤

### 1. 合并到你的 UniApp 项目

把 `miniapp/pages/` 和 `miniapp/utils/` 目录复制到你的 UniApp 项目中：

```
你的 UniApp 项目/
├── pages/
│   ├── index/index.vue   ← 合并（加浮标按钮）
│   └── chat/index.vue    ← 新增：AI 客服页
├── utils/
│   └── ai-api.js          ← 新增：API 封装
├── pages.json             ← 注册 chat 页面路由
│    追加: {"path": "pages/chat/index", "style": {}}
```

### 2. 配置后端地址

打开 `utils/ai-api.js`，修改 `API_BASE`：

```javascript
const API_BASE = 'https://你的后端域名/api/v1'
```

### 3. 小程序后台配置

微信公众平台 → 开发管理 → 服务器域名 → **request 合法域名**：
- 添加你的后端域名（如 `https://api.yourdomain.com`）

### 4. 首页加浮标

见 `pages/index/index.vue` — `ai-float-btn` 区块。

### 5. 用户 Token

用户登录后，把充电桩平台的 Bearer Token 存到 storage：

```javascript
uni.setStorageSync('token', '用户登录拿到的Token')
```

Token 自动被 `ai-api.js` 读取并带上。

## 项目结构

```
miniapp/
├── pages/
│   ├── index/index.vue    ← 首页（含 AI 浮标按钮）
│   └── chat/index.vue     ← AI 客服聊天页
├── utils/
│   └── ai-api.js          ← API 请求封装
├── App.vue                ← 应用入口
├── main.js                ← 入口 JS
├── manifest.json          ← 小程序配置
├── pages.json             ← 路由注册
└── README.md
```
