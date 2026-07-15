<?php
/**
 * PHP 模板示例 — 在页面中嵌入 AI 客服浮窗
 *
 * 将此代码放入你的 PHP 布局文件或首页模板中。
 * 假设你已经通过用户登录获得了 $currentUser 信息。
 */

// ── 1. 引入 JWT Helper ──────────────────────────────────────────
require_once __DIR__ . '/jwt_helper.php';

// ── 2. 从你的用户系统中获取当前用户信息 ───────────────────────────
// $currentUser = $_SESSION['user'] ?? null;
// 或者从你的框架中获取: Auth::user()

// ⚠️ 以下为示例，替换为你的实际用户获取逻辑
$currentUser = [
    'id'   => session_id() ?? 'anonymous',
    'name' => $_SESSION['username'] ?? '访客',
    'role' => 'user',
];

// ── 3. 生成 JWT Token ───────────────────────────────────────────
$aiToken = generate_ai_token(
    userId: $currentUser['id'],
    name:   $currentUser['name'],
    role:   $currentUser['role'],
);

// ── 4. 获取 AI 客服服务的地址 ─────────────────────────────────────
// 生产环境建议使用同域名反向代理（无跨域问题）
// 例如: Nginx 将 /ai-api/ 转发到 Python 服务的 8000 端口
$aiApiBase = '/ai-api/api/v1';  // 同域代理
// 如果 Python 服务独立部署:
// $aiApiBase = 'https://ai-api.yourdomain.com/api/v1';
?>

<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>你的 PHP 应用</title>
    <!-- ... 你的其他样式 ... -->
</head>
<body>
    <!-- 你的页面内容 -->
    <h1>欢迎 <?= htmlspecialchars($currentUser['name']) ?></h1>
    <!-- ... -->

    <?php
    // ── 5. 注入 JWT Token 到页面 ─────────────────────────────────
    echo render_ai_token_script($aiToken);
    ?>

    <!-- ── 6. 加载 AI 客服浮窗 Widget ──────────────────────────── -->
    <!--
      生产环境建议把 widget.js 托管到 CDN 或 PHP 项目的静态目录。
      如果 Python 和 PHP 同域，使用反向代理后的路径。
    -->
    <script
      src="http://localhost:8000/ai-widget/widget.js"
      data-api-base="<?= htmlspecialchars($aiApiBase) ?>"
      data-title="AI 客服助手"
      data-subtitle="智能解答"
      data-position="right"
      data-greeting="您好！我是 AI 客服助手，有什么可以帮您的吗？"
    ></script>

    <!-- 如果你不想用 data-* 属性传 token，也可以用全局变量方式 -->
    <!-- <script>window.__AI_TOKEN = "<?= $aiToken ?>";</script> -->
    <!-- <script src="/static/widget.js" data-api-base="<?= $aiApiBase ?>"></script> -->

</body>
</html>
