/**
 * AI 客服 API 封装
 *
 * 所有请求自动从 storage 取 Token 并带上 Authorization header。
 */

// 后端服务地址 — 小程序后台需配此域名到 request 白名单
// 开发时可以用 http://localhost:8000（需微信开发者工具不校验域名）
// 生产环境用你实际部署的域名
const API_BASE = import.meta.env.VITE_API_BASE || 'http://3d0e7225.r10.cpolar.top/api/v1'

function getToken() {
  try {
    return uni.getStorageSync('ai_token') || uni.getStorageSync('token') || ''
  } catch {
    return ''
  }
}

function request(method, path, data = {}) {
  const token = getToken()
  const header = { 'Content-Type': 'application/json' }
  if (token) header['Authorization'] = 'Bearer ' + token

  return new Promise((resolve, reject) => {
    uni.request({
      url: API_BASE + path,
      method,
      header,
      data,
      timeout: 30000,
      success(res) {
        if (res.statusCode === 401) {
          // Token 无效，通知用户重新登录
          uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
          reject(new Error('Unauthorized'))
          return
        }
        if (res.statusCode >= 400) {
          reject(new Error(res.data?.detail || '请求失败'))
          return
        }
        resolve(res.data)
      },
      fail(err) {
        reject(new Error('网络请求失败: ' + (err.errMsg || '未知错误')))
      }
    })
  })
}

/** 发送对话消息（非流式）— 使用较长的超时时间 */
function requestLong(method, path, data = {}, timeout = 120000) {
  const token = getToken()
  const header = { 'Content-Type': 'application/json' }
  if (token) header['Authorization'] = 'Bearer ' + token

  return new Promise((resolve, reject) => {
    uni.request({
      url: API_BASE + path,
      method,
      header,
      data,
      timeout,
      success(res) {
        if (res.statusCode === 401) {
          uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
          reject(new Error('Unauthorized'))
          return
        }
        if (res.statusCode >= 400) {
          reject(new Error(res.data?.detail || '请求失败'))
          return
        }
        resolve(res.data)
      },
      fail(err) {
        reject(new Error('网络请求失败: ' + (err.errMsg || '未知错误')))
      }
    })
  })
}

/** 发送对话消息（非流式）— AI 回答可能较慢，超时设为 120 秒 */
export function sendMessage(sessionId, message, intentHint) {
  const body = { session_id: sessionId, message }
  if (intentHint) body.intent_hint = intentHint
  return requestLong('POST', '/chat/completions', body)
}

/** 获取会话列表（分页） */
export function getSessions(userId, page = 1, pageSize = 50) {
  const params = { page, page_size: pageSize }
  if (userId) params.user_id = userId
  const qs = Object.keys(params).map(k => k + '=' + encodeURIComponent(params[k])).join('&')
  return request('GET', '/sessions' + (qs ? '?' + qs : ''))
}

/** 获取会话消息历史 */
export function getSessionMessages(sessionId) {
  return request('GET', '/sessions/' + encodeURIComponent(sessionId) + '/messages')
}

/** 创建会话 */
export function createSession(sessionId, title, userId) {
  return request('POST', '/sessions', { id: sessionId, title, user_id: userId })
}

/** 提交反馈 */
export function submitFeedback(messageId, rating, comment) {
  return request('POST', '/feedback', { message_id: messageId, rating, comment })
}

/** 获取提示词列表 */
export function getPrompts() {
  return request('GET', '/prompts')
}

/** 获取用户信息（通过外部 API） */
export function getUserInfo() {
  return request('GET', '/proxy/home/statUsers', { pageNum: 1, pageSize: 1 })
}

/** 健康检查 */
export function healthCheck() {
  return request('GET', '/admin/health')
}
