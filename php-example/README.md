# PHP 集成指南 — 将 AI 客服浮窗嵌入你的 PHP App

## 集成步骤（3 步搞定）

### 步骤 1：在你的 PHP 项目中安装 JWT 库

```bash
composer require firebase/php-jwt
```

### 步骤 2：约定 JWT Secret

确保 PHP 端和 Python 端使用**相同的 JWT Secret**：

| 配置 | PHP (jwt_helper.php) | Python (.env) |
|:--|:--|:--|
| JWT Secret | `AI_JWT_SECRET` | `JWT_SECRET_KEY` |
| 算法 | `AI_JWT_ALGORITHM = HS256` | `JWT_ALGORITHM = HS256` |
| 过期时间 | `AI_JWT_EXPIRY = 86400` | `JWT_EXPIRATION_MINUTES = 1440` |

> ⚠️ 生产环境务必使用强随机字符串作为 JWT Secret，不要用默认值。

### 步骤 3：在页面模板中插入 Widget

把 `embed_template.php` 中的代码逻辑放到你的布局文件里即可。

---

## 架构方案选择

### 方案 A：同域反向代理（推荐 ✅）

```
用户 → PHP 域名 (app.com) → Nginx → /ai-api/ → Python:8000
                                    → / → PHP-FPM
```

- ✅ 无跨域问题
- ✅ Cookie 自动透传
- ✅ 无需改防火墙
- ✅ WebSocket 支持

参考 `nginx-proxy.conf` 配置。

### 方案 B：跨域独立部署

```
用户 → PHP (app.com) ── JS 直接请求 ──→ Python (ai-api.com)
```

- 需要 Python 端配置 CORS 允许 `app.com`
- 需要 WebSocket 跨域配置（更复杂）

---

## Token 刷新机制

JWT 默认 24 小时过期。有以下几种处理方式：

1. **用户刷新页面时更新**（最简单）
   - PHP 页面每次渲染都生成新 token
   - 用户刷新页面即获得新 token

2. **JS 定时刷新**
   - 前端定时调用 `/api/v1/auth/refresh` 接口换新 token
   - 需要旧 token 有效

3. **滑动过期**
   - 用户在持续使用时不生成新 token
   - 适合对安全性要求不高的场景

---

## 常见问题

**Q: Widget 样式和我的页面冲突了怎么办？**
A: 所有样式都加上了 `.aic-` 前缀，不会污染全局样式。

**Q: 生产环境 widget.js 放哪里？**
A: 推荐放在你的 PHP 项目静态目录下，用 Nginx 直接 serve。或上传到 CDN。

**Q: 如何关闭 AI 客服功能？**
A: 移除模板中的 `<script>` 标签即可。

**Q: 用户未登录时能用吗？**
A: 可以，不传 token 则匿名访问，不影响对话功能。
