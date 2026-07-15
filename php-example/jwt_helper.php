<?php
/**
 * JWT Helper — PHP 端生成 JWT Token 供 Python AI 客服验证
 *
 * 使用方法:
 *   1. 复制此文件到你的 PHP 项目中
 *   2. 在 composer.json 中添加 firebase/php-jwt 依赖
 *   3. 用户登录后，调用 generate_ai_token() 生成 JWT
 *   4. 将 token 注入到页面中
 *
 * 依赖: firebase/php-jwt (composer require firebase/php-jwt)
 */

require_once __DIR__ . '/vendor/autoload.php';

use Firebase\JWT\JWT;
use Firebase\JWT\Key;

/**
 * AI 客服 JWT 配置
 * 这些值必须与 Python 端 .env 中的 JWT_SECRET_KEY / JWT_ALGORITHM 一致
 */
define('AI_JWT_SECRET', 'your-jwt-secret-here');    // 与 Python .env JWT_SECRET_KEY 相同
define('AI_JWT_ALGORITHM', 'HS256');                 // 与 Python .env JWT_ALGORITHM 相同
define('AI_JWT_EXPIRY', 86400);                      // 过期时间（秒），默认 24 小时
define('AI_JWT_ISSUER', 'aicustomerservice');        // 与 Python .env JWT_ISSUER 相同

/**
 * 生成 AI 客服 JWT Token
 *
 * @param string $userId   用户 ID（必填，用于关联对话记录）
 * @param string $name     用户昵称（可选，用于展示）
 * @param string $role     角色（user | admin）
 * @param int    $expiry   过期时间（秒），默认 24 小时
 *
 * @return string JWT Token
 */
function generate_ai_token(
    string $userId,
    string $name = '',
    string $role = 'user',
    int $expiry = AI_JWT_EXPIRY
): string {
    $now = time();
    $payload = [
        'sub'  => $userId,           // 用户 ID
        'name' => $name,             // 用户昵称
        'role' => $role,             // 角色
        'iss'  => AI_JWT_ISSUER,     // 签发者
        'iat'  => $now,              // 签发时间
        'exp'  => $now + $expiry,    // 过期时间
    ];

    return JWT::encode($payload, AI_JWT_SECRET, AI_JWT_ALGORITHM);
}

/**
 * 验证 AI 客服 JWT Token（供 PHP 端调试用）
 *
 * @param string $token
 * @return object|null 成功返回 payload，失败返回 null
 */
function verify_ai_token(string $token): ?object
{
    try {
        return JWT::decode($token, new Key(AI_JWT_SECRET, AI_JWT_ALGORITHM));
    } catch (\Exception $e) {
        return null;
    }
}

/**
 * 获取页面中注入的 AI Token（用于 JS 读取）
 *
 * @param string $token
 * @return string HTML script 标签
 */
function render_ai_token_script(string $token): string
{
    $escaped = htmlspecialchars($token, ENT_QUOTES, 'UTF-8');
    return '<script>window.__AI_TOKEN = ' . json_encode($escaped) . ';</script>';
}
