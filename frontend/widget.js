/**
 * AiCustomerService Widget — 可嵌入的 AI 客服浮窗
 *
 * 用法（在 PHP 页面中）:
 *   <script src="/ai-widget/widget.js"
 *     data-api-base="http://localhost:8000/api/v1"
 *     data-title="AI 客服助手"
 *     data-token="<JWT_TOKEN>"
 *     data-position="right"
 *   ></script>
 *
 * 或用 Token 注入方式:
 *   <script>window.__AI_TOKEN = "<JWT_TOKEN>";</script>
 *   <script src="/ai-widget/widget.js" data-api-base="..."></script>
 *
 * 纯原生 JS，零依赖。
 */

(function () {
  'use strict';

  // ── 配置 ────────────────────────────────────────────────────────
  const script = document.currentScript;
  const cfg = {
    apiBase: script?.getAttribute('data-api-base') || '/api/v1',
    wsBase: script?.getAttribute('data-ws-base') || '',
    title: script?.getAttribute('data-title') || 'AI 客服助手',
    subtitle: script?.getAttribute('data-subtitle') || '在线智能解答',
    position: script?.getAttribute('data-position') || 'right', // right | left
    color: script?.getAttribute('data-color') || '#0f3460',
    accentColor: script?.getAttribute('data-accent') || '#e94560',
    width: parseInt(script?.getAttribute('data-width') || '360', 10),
    height: parseInt(script?.getAttribute('data-height') || '520', 10),
    buttonSize: parseInt(script?.getAttribute('data-btn-size') || '56', 10),
    placeholder: script?.getAttribute('data-placeholder') || '输入您的问题...',
    greeting: script?.getAttribute('data-greeting') || '您好！我是 AI 客服助手，有什么可以帮您的吗？',
  };

  // ── Token ───────────────────────────────────────────────────────
  function getToken() {
    return window.__AI_TOKEN || script?.getAttribute('data-token') || '';
  }

  // ── HTTP 请求 ──────────────────────────────────────────────────
  async function apiPost(path, body) {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const res = await fetch(cfg.apiBase + path, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(res.status + (text ? ': ' + text.slice(0, 200) : ''));
    }
    return res.json();
  }

  async function apiGet(path, params) {
    const headers = {};
    const token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const qs = params ? '?' + new URLSearchParams(params) : '';
    const res = await fetch(cfg.apiBase + path + qs, { headers });
    if (!res.ok) throw new Error(res.status);
    return res.json();
  }

  // ── UUID 生成 ──────────────────────────────────────────────────
  function uuid() {
    return crypto.randomUUID
      ? crypto.randomUUID()
      : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
          const r = (Math.random() * 16) | 0;
          return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
        });
  }

  // ── 简易 Markdown 渲染 ──────────────────────────────────────────
  function renderMarkdown(text) {
    if (!text) return '';
    let h = escapeHtml(text);

    // 代码块
    const blocks = [];
    h = h.replace(
      /```(\w*)\n([\s\S]*?)```/g,
      (_, lang, code) => {
        const i = blocks.length;
        blocks.push(`<pre><code>${escapeHtml(code.trim())}</code></pre>`);
        return `%%CB${i}%%`;
      }
    );

    // 行内代码
    h = h.replace(/`([^`]+)`/g, '<code>$1</code>');

    // 图片
    h = h.replace(
      /!\[([^\]]*)\]\(([^)]+)\)/g,
      '<img src="$2" alt="$1" loading="lazy" style="max-width:100%;border-radius:6px;margin:4px 0" onerror="this.style.display=\'none\'">'
    );

    // 标题
    h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // 粗斜体
    h = h.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // 链接
    h = h.replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>'
    );

    // 列表
    h = h.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
    h = h.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    h = h.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // 换行
    h = h.replace(/\n/g, '<br>');

    // 恢复代码块
    h = h.replace(/%%CB(\d+)%%/g, (_, i) => blocks[i] || '');
    return h;
  }

  function escapeHtml(t) {
    return String(t)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  // ── 时间格式化 ──────────────────────────────────────────────────
  function formatTime(d) {
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
    const h = String(d.getHours()).padStart(2, '0');
    const m = String(d.getMinutes()).padStart(2, '0');
    if (d.toDateString() === now.toDateString()) return h + ':' + m;
    return d.getMonth() + 1 + '/' + d.getDate() + ' ' + h + ':' + m;
  }

  // ── 创建 DOM ───────────────────────────────────────────────────
  function createElement(html) {
    const div = document.createElement('div');
    div.innerHTML = html.trim();
    return div.firstElementChild;
  }

  // ── 主组件 ──────────────────────────────────────────────────────
  function Widget() {
    this.sessionId = uuid();
    this.messages = [];
    this.loading = false;
    this.open = false;

    this._build();
    this._bindEvents();
    // 如果用户开启了 ws，尝试连接（暂不实现）
  }

  Widget.prototype._build = function () {
    const isRight = cfg.position === 'right';

    // 样式
    const style = document.createElement('style');
    style.textContent = `
/* ── AI Widget ────────── */
.aic-widget *,.aic-widget *::before,.aic-widget *::after{box-sizing:border-box;margin:0;padding:0}
.aic-widget{font-family:-apple-system,"Microsoft YaHei","PingFang SC",sans-serif;color:#333;line-height:1.5;z-index:2147483647}
.aic-widget a{color:${cfg.color};text-decoration:none}
.aic-widget a:hover{text-decoration:underline}

/* ── 浮窗按钮 ── */
.aic-btn{position:fixed;${isRight ? 'right' : 'left'}:20px;bottom:20px;width:${cfg.buttonSize}px;height:${cfg.buttonSize}px;border-radius:50%;background:${cfg.color};color:#fff;border:none;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.2);display:flex;align-items:center;justify-content:center;font-size:26px;transition:transform .25s,box-shadow .25s;z-index:2147483647;touch-action:manipulation}
.aic-btn:hover{transform:scale(1.08);box-shadow:0 6px 24px rgba(0,0,0,.28)}
.aic-btn:active{transform:scale(.95)}
.aic-btn.aic-open{transform:rotate(45deg) scale(.9);background:#666}
.aic-btn .aic-badge{position:absolute;top:-2px;${isRight ? 'right' : 'left'}:-2px;background:${cfg.accentColor};color:#fff;font-size:10px;padding:2px 6px;border-radius:10px;min-width:18px;text-align:center;font-weight:600;display:none}

/* ── 聊天面板 ── */
.aic-panel{position:fixed;${isRight ? 'right' : 'left'}:20px;bottom:${parseInt(cfg.buttonSize) + 24}px;width:${cfg.width}px;height:${cfg.height}px;background:#fff;border-radius:16px;box-shadow:0 8px 40px rgba(0,0,0,.18);display:flex;flex-direction:column;overflow:hidden;transition:transform .3s,opacity .3s;transform-origin:${isRight ? 'bottom right' : 'bottom left'};z-index:2147483646}
.aic-panel.aic-hidden{transform:scale(.85);opacity:0;pointer-events:none}

/* ── 头部 ── */
.aic-header{background:${cfg.color};color:#fff;padding:14px 16px;display:flex;align-items:center;gap:10px;flex-shrink:0;cursor:pointer;user-select:none}
.aic-header .aic-avatar{width:32px;height:32px;border-radius:50%;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.aic-header .aic-header-info{flex:1;min-width:0}
.aic-header .aic-header-title{font-size:14px;font-weight:600}
.aic-header .aic-header-sub{font-size:11px;opacity:.8;margin-top:1px}
.aic-header .aic-close-btn{background:none;border:none;color:rgba(255,255,255,.7);font-size:20px;cursor:pointer;padding:0 2px;line-height:1;transition:color .2s}
.aic-header .aic-close-btn:hover{color:#fff}

/* ── 消息区 ── */
.aic-msgs{flex:1;overflow-y:auto;padding:12px 14px;background:#f5f6f8;scroll-behavior:smooth}
.aic-msgs::-webkit-scrollbar{width:4px}
.aic-msgs::-webkit-scrollbar-thumb{background:#ccc;border-radius:4px}

.aic-msg{display:flex;gap:8px;margin-bottom:14px;animation:aicFadeIn .25s ease}
@keyframes aicFadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.aic-msg.aic-user{flex-direction:row-reverse}
.aic-msg .aic-av{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0}
.aic-msg.aic-bot .aic-av{background:${cfg.color};color:#fff}
.aic-msg.aic-user .aic-av{background:${cfg.accentColor};color:#fff}
.aic-msg .aic-bubble{max-width:82%;padding:9px 12px;border-radius:12px;font-size:13px;line-height:1.6;word-break:break-word}
.aic-msg.aic-user .aic-bubble{background:${cfg.accentColor};color:#fff;border-bottom-right-radius:4px}
.aic-msg.aic-bot .aic-bubble{background:#fff;color:#333;border-bottom-left-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.aic-msg .aic-time{font-size:10px;color:#aaa;margin-top:2px;padding:0 2px}
.aic-msg.aic-user .aic-time{text-align:right}

.aic-msg .aic-bubble h1,.aic-msg .aic-bubble h2,.aic-msg .aic-bubble h3{font-size:14px;font-weight:600;margin:4px 0 2px}
.aic-msg .aic-bubble p{margin:2px 0}
.aic-msg .aic-bubble ul,.aic-msg .aic-bubble ol{padding-left:16px;margin:2px 0}
.aic-msg .aic-bubble code{background:#f0f2f5;padding:1px 4px;border-radius:3px;font-size:12px}
.aic-msg .aic-bubble pre{background:#1a1a2e;color:#e6e6e6;padding:8px 12px;border-radius:6px;overflow-x:auto;margin:4px 0;font-size:12px}
.aic-msg .aic-bubble pre code{background:none;padding:0;color:inherit}
.aic-msg .aic-bubble img{max-width:100%;border-radius:6px;margin:3px 0}
.aic-msg .aic-bubble table{border-collapse:collapse;margin:4px 0;font-size:12px;width:100%}
.aic-msg .aic-bubble th,.aic-msg .aic-bubble td{border:1px solid #ddd;padding:4px 6px;text-align:left}
.aic-msg .aic-bubble th{background:#f8f9fa;font-weight:600}
.aic-source{font-size:11px;color:#888;padding:3px 0 0;border-top:1px solid #eee;margin-top:4px}
.aic-source-item{display:inline-block;font-size:10px;background:#f0f2f5;padding:1px 6px;border-radius:4px;margin:1px 2px 1px 0;color:#666}

/* ── 加载动画 ── */
.aic-typing{display:flex;gap:3px;padding:4px 0}
.aic-typing span{width:6px;height:6px;border-radius:50%;background:#bbb;animation:aicTyping 1.4s infinite}
.aic-typing span:nth-child(2){animation-delay:.2s}
.aic-typing span:nth-child(3){animation-delay:.4s}
@keyframes aicTyping{0%,60%,100%{opacity:.3;transform:scale(.8)}30%{opacity:1;transform:scale(1)}}
.aic-thinking{font-size:11px;color:#999}

/* ── 输入区 ── */
.aic-input-area{display:flex;gap:8px;padding:10px 14px;background:#fff;border-top:1px solid #e8e8e8;align-items:flex-end;flex-shrink:0}
.aic-input-area textarea{flex:1;border:1px solid #d9d9d9;border-radius:8px;padding:8px 10px;font-size:13px;resize:none;outline:none;font-family:inherit;line-height:1.5;min-height:36px;max-height:100px;transition:border-color .2s}
.aic-input-area textarea:focus{border-color:${cfg.color}}
.aic-input-area button{width:36px;height:36px;border-radius:50%;background:${cfg.color};color:#fff;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;transition:opacity .2s}
.aic-input-area button:hover{opacity:.85}
.aic-input-area button:disabled{opacity:.35;cursor:not-allowed}
.aic-input-area button svg{width:18px;height:18px;fill:currentColor}

/* ── 空状态 ── */
.aic-empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#bbb;font-size:13px;padding:40px}
.aic-empty .aic-empty-icon{font-size:36px;margin-bottom:8px}

/* ── 响应式 ── */
@media(max-width:480px){
  .aic-panel{${isRight ? 'right' : 'left'}:0!important;bottom:0!important;width:100%!important;height:100%!important;border-radius:0!important}
  .aic-btn{bottom:16px;${isRight ? 'right' : 'left'}:16px}
}
`.trim();
    document.head.appendChild(style);

    // 容器
    this.el = createElement('<div class="aic-widget"></div>');

    // 按钮
    this.btn = createElement(
      `<button class="aic-btn" aria-label="打开AI客服" title="${cfg.title}">
        <span class="aic-badge">1</span>
        <span>💬</span>
      </button>`
    );

    // 面板
    this.panel = createElement(
      `<div class="aic-panel aic-hidden">
        <div class="aic-header">
          <div class="aic-avatar">🤖</div>
          <div class="aic-header-info">
            <div class="aic-header-title">${escapeHtml(cfg.title)}</div>
            <div class="aic-header-sub">${escapeHtml(cfg.subtitle)}</div>
          </div>
          <button class="aic-close-btn" aria-label="关闭">✕</button>
        </div>
        <div class="aic-msgs">
          <div class="aic-empty">
            <div class="aic-empty-icon">💬</div>
            <div>${escapeHtml(cfg.greeting)}</div>
          </div>
        </div>
        <div class="aic-input-area">
          <textarea rows="1" placeholder="${escapeHtml(cfg.placeholder)}"></textarea>
          <button disabled aria-label="发送">
            <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
          </button>
        </div>
      </div>`
    );

    this.msgsEl = this.panel.querySelector('.aic-msgs');
    this.inputEl = this.panel.querySelector('textarea');
    this.sendBtn = this.panel.querySelector('.aic-input-area button');
    this.emptyEl = this.msgsEl.querySelector('.aic-empty');

    this.el.appendChild(this.btn);
    this.el.appendChild(this.panel);
    document.body.appendChild(this.el);
  };

  Widget.prototype._bindEvents = function () {
    const self = this;

    // 按钮点击切换面板
    this.btn.addEventListener('click', function (e) {
      e.stopPropagation();
      self.toggle();
    });

    // 关闭按钮
    this.panel.querySelector('.aic-close-btn').addEventListener('click', function () {
      self.close();
    });

    // 头部点击也关闭
    this.panel.querySelector('.aic-header').addEventListener('click', function () {
      self.close();
    });

    // 输入框事件
    this.inputEl.addEventListener('input', function () {
      self._autoResize();
      self.sendBtn.disabled = !this.value.trim().length || self.loading;
    });

    this.inputEl.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        self.send();
      }
    });

    // 发送按钮
    this.sendBtn.addEventListener('click', function () {
      self.send();
    });

    // 点击外部关闭
    document.addEventListener('click', function (e) {
      if (self.open && !self.el.contains(e.target)) {
        self.close();
      }
    });
  };

  Widget.prototype.toggle = function () {
    this.open ? this.close() : this.open_();
  };

  Widget.prototype.open_ = function () {
    this.open = true;
    this.btn.classList.add('aic-open');
    this.panel.classList.remove('aic-hidden');
    this.btn.querySelector('.aic-badge').style.display = 'none';
    this.inputEl.focus();
    // 加载会话列表（如果有 token）
    if (getToken()) this._loadSessions();
  };

  Widget.prototype.close = function () {
    this.open = false;
    this.btn.classList.remove('aic-open');
    this.panel.classList.add('aic-hidden');
  };

  // ── 会话管理 ──────────────────────────────────────────────────
  Widget.prototype._loadSessions = async function () {
    try {
      const data = await apiGet('/sessions', { user_id: getToken() ? undefined : undefined });
      // 暂不显示会话列表，保留为后续扩展
    } catch (e) {
      // 静默失败
    }
  };

  // ── 发送消息 ──────────────────────────────────────────────────
  Widget.prototype.send = function () {
    const text = this.inputEl.value.trim();
    if (!text || this.loading) return;
    this.inputEl.value = '';
    this._autoResize();
    this.sendBtn.disabled = true;

    // 移除空状态
    if (this.emptyEl) {
      this.emptyEl.remove();
      this.emptyEl = null;
    }

    // 添加用户消息
    this._addMessage('user', text);
    this._scrollBottom();

    // 添加加载占位
    const botId = 'aic-msg-' + uuid();
    const botBubble = this.msgsEl;
    botBubble.insertAdjacentHTML(
      'beforeend',
      `<div class="aic-msg aic-bot" id="${botId}">
        <div class="aic-av">🤖</div>
        <div class="aic-bubble">
          <div class="aic-typing"><span></span><span></span><span></span></div>
          <div class="aic-thinking">思考中...</div>
        </div>
      </div>`
    );
    this._scrollBottom();
    this.loading = true;

    // 保存 session
    this._ensureSession(text);

    // 发送请求
    this._doChat(text)
      .then((result) => {
        const botEl = document.getElementById(botId);
        if (!botEl) return;
        const bubble = botEl.querySelector('.aic-bubble');
        if (!bubble) return;

        // 替换占位为实际回答
        bubble.innerHTML = renderMarkdown(result.answer || '');

        // 来源
        if (result.sources && result.sources.length) {
          const srcDiv = document.createElement('div');
          srcDiv.className = 'aic-source';
          const shown = result.sources.filter((s) => s.doc_name && !s.doc_name.startsWith('API:'));
          if (shown.length) {
            shown.forEach((s) => {
              const el = document.createElement('span');
              el.className = 'aic-source-item';
              el.textContent = '📄 ' + s.doc_name;
              srcDiv.appendChild(el);
            });
            bubble.appendChild(srcDiv);
          }
        }
        this._scrollBottom();
      })
      .catch((err) => {
        const botEl = document.getElementById(botId);
        if (!botEl) return;
        const bubble = botEl.querySelector('.aic-bubble');
        if (bubble) {
          bubble.innerHTML =
            err.message.includes('401') || err.message.includes('403')
              ? '⚠️ 身份验证已过期，请刷新页面重试。'
              : '😅 抱歉，我遇到了问题，请稍后再试。';
        }
        this._scrollBottom();
      })
      .finally(() => {
        this.loading = false;
        this.sendBtn.disabled = !this.inputEl.value.trim().length;
      });
  };

  Widget.prototype._ensureSession = function (text) {
    // 后端会在 chat 接口中自动创建 session，不需要单独调
    // 这里留空，有需要可以添加
  };

  Widget.prototype._doChat = async function (text) {
    const body = {
      session_id: this.sessionId,
      message: text,
    };
    // 如果有 token，不需要传 user_id（后端从 JWT 提取）
    if (!getToken()) {
      body.user_id = 'widget-anon';
    }
    return apiPost('/chat/completions', body);
  };

  Widget.prototype._addMessage = function (role, content) {
    const isUser = role === 'user';
    const bubble = isUser ? escapeHtml(content).replace(/\n/g, '<br>') : renderMarkdown(content);
    const html = `
      <div class="aic-msg ${isUser ? 'aic-user' : 'aic-bot'}">
        <div class="aic-av">${isUser ? '👤' : '🤖'}</div>
        <div>
          <div class="aic-bubble">${bubble}</div>
          <div class="aic-time">${formatTime(new Date())}</div>
        </div>
      </div>`;
    this.msgsEl.insertAdjacentHTML('beforeend', html);
  };

  Widget.prototype._scrollBottom = function () {
    requestAnimationFrame(() => {
      this.msgsEl.scrollTop = this.msgsEl.scrollHeight;
    });
  };

  Widget.prototype._autoResize = function () {
    this.inputEl.style.height = 'auto';
    this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 100) + 'px';
  };

  // ── 初始化 ──────────────────────────────────────────────────────
  function init() {
    // 避免重复加载
    if (window.__AiCustomerWidget) return;
    window.__AiCustomerWidget = new Widget();

    // 如果有 badge 内容，显示小红点（可配置）
    // 默认隐藏
  }

  // 等 DOM 加载完成
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init);
  }
})();
