<template>
  <view class="chat-page">
    <!-- 导航栏 -->
    <view class="nav-bar">
      <view class="nav-left">
        <text class="nav-back-icon" @click="goBack">←</text>
        <text class="nav-hist-btn" @click="toggleHistory">📋</text>
      </view>
      <view class="nav-info">
        <text class="nav-title">AI 智能客服</text>
        <text class="nav-subtitle">{{ statusText }}</text>
      </view>
      <view class="nav-right">
        <text class="nav-new-btn" @click="newChat">✚</text>
      </view>
    </view>

    <!-- 历史记录面板 -->
    <view class="hist-overlay" v-if="showHistory" @click="closeHistory"></view>
    <view class="hist-panel" :class="{ 'hist-open': showHistory }">
      <view class="hist-header">
        <text class="hist-title">历史对话</text>
        <text class="hist-close" @click="closeHistory">✕</text>
      </view>
      <scroll-view class="hist-list" scroll-y>
        <!-- 今日 -->
        <view v-if="groupedSessions.today.length" class="hist-group">
          <text class="hist-group-label">今天</text>
          <view
            v-for="s in groupedSessions.today" :key="s.id"
            class="hist-item" @click="loadSession(s)"
          >
            <text class="hist-item-title">{{ s.title || '新对话' }}</text>
            <text class="hist-item-time">{{ formatSessionTime(s.updated_at || s.created_at) }}</text>
          </view>
        </view>
        <!-- 昨天 -->
        <view v-if="groupedSessions.yesterday.length" class="hist-group">
          <text class="hist-group-label">昨天</text>
          <view
            v-for="s in groupedSessions.yesterday" :key="s.id"
            class="hist-item" @click="loadSession(s)"
          >
            <text class="hist-item-title">{{ s.title || '新对话' }}</text>
            <text class="hist-item-time">{{ formatSessionTime(s.updated_at || s.created_at) }}</text>
          </view>
        </view>
        <!-- 近7天 -->
        <view v-if="groupedSessions.week.length" class="hist-group">
          <text class="hist-group-label">近7天</text>
          <view
            v-for="s in groupedSessions.week" :key="s.id"
            class="hist-item" @click="loadSession(s)"
          >
            <text class="hist-item-title">{{ s.title || '新对话' }}</text>
            <text class="hist-item-time">{{ formatSessionTime(s.updated_at || s.created_at) }}</text>
          </view>
        </view>
        <!-- 空状态 -->
        <view v-if="!groupedSessions.today.length && !groupedSessions.yesterday.length && !groupedSessions.week.length" class="hist-empty">
          <text>暂无历史记录</text>
        </view>
      </scroll-view>
    </view>

    <!-- 消息列表 -->
    <view class="msg-list" id="msg-list" ref="msgList">
      <!-- 提示词列表（始终显示） -->
      <view class="prompts-wrap">
        <view class="prompts-tabs">
          <text
            class="prompts-tab"
            :class="{ 'prompts-tab-active': promptTab === 'all' }"
            @click="promptTab = 'all'"
          >全部</text>
          <text
            class="prompts-tab"
            :class="{ 'prompts-tab-active': promptTab === 'revenue' }"
            @click="promptTab = 'revenue'"
          >运营收益</text>
          <text
            class="prompts-tab"
            :class="{ 'prompts-tab-active': promptTab === 'orders' }"
            @click="promptTab = 'orders'"
          >用户订单</text>
          <text
            class="prompts-tab"
            :class="{ 'prompts-tab-active': promptTab === 'device' }"
            @click="promptTab = 'device'"
          >设备相关</text>
        </view>
        <text class="prompts-title">💡 试试问这些</text>
        <view
          v-for="(item, idx) in currentPrompts"
          :key="idx"
          class="prompt-item"
          @click="sendPrompt(item.text, item.intent)"
        >
          <text class="prompt-text">{{ item.text }}</text>
          <text class="prompt-arrow">➤</text>
        </view>
        <view class="prompts-footer">
          <text class="prompts-page">{{ promptPage }}/{{ totalPromptPages }}</text>
          <text class="prompts-next" @click="nextPrompts">换一批 →</text>
        </view>
      </view>

      <view
        v-for="(msg, idx) in messages"
        :key="msg.id"
        class="msg-item"
        :class="msg.role === 'user' ? 'msg-user' : 'msg-bot'"
      >
        <view class="msg-avatar">
          <text>{{ msg.role === 'user' ? '👤' : '🤖' }}</text>
        </view>
        <view class="msg-content">
          <view class="msg-bubble">
            <rich-text
              v-if="msg.role === 'bot'"
              :nodes="renderMarkdown(msg.content)"
              class="rich-text"
            ></rich-text>
            <text v-else class="user-text">{{ msg.content }}</text>

            <!-- 来源引用 -->
            <view v-if="msg.sources && msg.sources.length" class="msg-sources">
              <view
                v-for="(src, si) in msg.sources.filter(s => s.doc_name && !s.doc_name.startsWith('API:'))"
                :key="si"
                class="source-item"
              >
                <text class="source-icon">📄</text>
                <text class="source-name">{{ src.doc_name }}</text>
              </view>
            </view>
          </view>
          <text class="msg-time">{{ msg.time }}</text>
        </view>
      </view>

      <!-- 思考中占位 -->
      <view v-if="loading" class="msg-item msg-bot">
        <view class="msg-avatar"><text>🤖</text></view>
        <view class="msg-content">
          <view class="msg-bubble thinking-bubble">
            <view class="thinking-dots">
              <view class="dot"></view>
              <view class="dot"></view>
              <view class="dot"></view>
            </view>
            <text class="thinking-text">思考中...</text>
          </view>
        </view>
      </view>

      <!-- 底部占位 -->
      <view style="height: 20rpx"></view>
    </view>

    <!-- 输入区 -->
    <view class="input-area" :class="{ 'input-safe': isIphoneX }">
      <view class="input-wrapper">
        <input
          class="input-box"
          v-model="inputText"
          type="text"
          :placeholder="loading ? '请等待回复...' : '输入您的问题...'"
          :disabled="loading"
          confirm-type="send"
          @confirm="sendMessage"
          @input="onInput"
        />
        <view
          class="send-btn"
          :class="{ 'send-btn-disabled': !inputText.trim() || loading }"
          @click="sendMessage"
        >
          <text class="send-icon">发送</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { sendMessage as apiSendMessage, createSession, getSessionMessages, getSessions } from '@/utils/ai-api.js'

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

function formatTime() {
  const d = new Date()
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return h + ':' + m
}

export default {
  data() {
    return {
      sessionId: '',
      messages: [],
      inputText: '',
      loading: false,
      statusText: '在线',
      isIphoneX: false,
      hasMoreHistory: false,
      showHistory: false,
      sessions: [],
      groupedSessions: { today: [], yesterday: [], week: [] },
      promptTab: 'all',
      promptPage: 1,
      pendingIntent: null,
      allPrompts: [
        { text: '本周收益情况',           cat: 'revenue', intent: 'DATA_QUERY' },
        { text: '本月收益情况',           cat: 'revenue', intent: 'DATA_QUERY' },
        { text: '有哪些增加收益的策略',    cat: 'revenue', intent: 'KB_QA' },
        { text: '上个月收益对比',         cat: 'revenue', intent: 'DATA_QUERY' },
        { text: '本季度订单趋势',         cat: 'revenue', intent: 'DATA_QUERY' },
        { text: '近7天营收趋势',          cat: 'revenue', intent: 'DATA_QUERY' },
        { text: '昨日电量统计',           cat: 'revenue', intent: 'DATA_QUERY' },
        { text: '我的收益什么时候到账',   cat: 'revenue', intent: 'KB_QA' },
        { text: '今日订单数量',           cat: 'orders', intent: 'DATA_QUERY' },
        { text: '渠道钱包如何提现',       cat: 'orders', intent: 'KB_QA' },
        { text: '为什么打开金额比结算收益少了', cat: 'orders', intent: 'KB_QA' },
        { text: '如何查看对账单',         cat: 'orders', intent: 'KB_QA' },
        { text: '站点收益排行榜',         cat: 'orders', intent: 'DATA_QUERY' },
        { text: '充电桩设备状态',         cat: 'device', intent: 'DATA_QUERY' },
        { text: '安心充开通收益',         cat: 'device', intent: 'KB_QA' },
      ]
    }
  },

  onLoad() {
    this.initSession()
    this.checkDevice()
  },

  computed: {
    filteredPrompts() {
      if (this.promptTab === 'all') return this.allPrompts
      return this.allPrompts.filter(p => p.cat === this.promptTab)
    },
    currentPrompts() {
      const start = (this.promptPage - 1) * 5
      return this.filteredPrompts.slice(start, start + 5)
    },
    totalPromptPages() {
      return Math.ceil(this.filteredPrompts.length / 5)
    }
  },
  methods: {
    // ── 初始化 ──
    initSession() {
      // 从 storage 取上次会话 ID
      const lastSession = uni.getStorageSync('ai_last_session') || ''
      if (lastSession) {
        this.sessionId = lastSession
        this.loadMessages(lastSession)
      } else {
        this.sessionId = generateId()
      }
    },

    checkDevice() {
      try {
        const info = uni.getSystemInfoSync()
        // 简单判断 iPhone X 系列刘海屏
        this.isIphoneX = info.safeArea && info.safeArea.bottom < info.windowHeight
      } catch(e) {}
    },

    goBack() {
      uni.navigateBack()
    },

    // ── 新对话 ──
    newChat() {
      this.sessionId = generateId()
      this.messages = []
      this.inputText = ''
      uni.setStorageSync('ai_last_session', this.sessionId)
    },

    // ── 提示词 ──
    sendPrompt(text, intent) {
      this.inputText = text
      this.pendingIntent = intent
      this.sendMessage()
    },
    nextPrompts() {
      if (this.promptPage < this.totalPromptPages) {
        this.promptPage++
      } else {
        this.promptPage = 1
      }
    },

    // ── 历史记录 ──
    toggleHistory() {
      this.showHistory = !this.showHistory
      if (this.showHistory) this.fetchSessions()
    },
    closeHistory() {
      this.showHistory = false
    },

    async fetchSessions() {
      try {
        const data = await getSessions()
        this.sessions = data.items || []
        this.groupSessions()
      } catch(e) {
        console.log('获取历史记录失败:', e.message)
      }
    },

    groupSessions() {
      const groups = { today: [], yesterday: [], week: [] }
      const now = new Date()
      const todayStr = now.toDateString()
      const yesterdayDate = new Date(now)
      yesterdayDate.setDate(yesterdayDate.getDate() - 1)
      const yesterdayStr = yesterdayDate.toDateString()
      const weekAgo = new Date(now)
      weekAgo.setDate(weekAgo.getDate() - 7)

      this.sessions.forEach(s => {
        const d = new Date(s.updated_at || s.created_at)
        if (d.toDateString() === todayStr) {
          groups.today.push(s)
        } else if (d.toDateString() === yesterdayStr) {
          groups.yesterday.push(s)
        } else if (d >= weekAgo) {
          groups.week.push(s)
        }
      })
      this.groupedSessions = groups
    },

    formatSessionTime(isoStr) {
      if (!isoStr) return ''
      const d = new Date(isoStr)
      if (isNaN(d.getTime())) return ''
      const h = String(d.getHours()).padStart(2, '0')
      const m = String(d.getMinutes()).padStart(2, '0')
      return h + ':' + m
    },

    async loadSession(session) {
      this.closeHistory()
      this.sessionId = session.id
      uni.setStorageSync('ai_last_session', session.id)
      this.messages = []
      await this.loadMessages(session.id)
      this.$nextTick(() => this.scrollToBottom())
    },

    // ── 消息加载 ──
    async loadMessages(sessionId) {
      try {
        const msgs = await getSessionMessages(sessionId)
        if (msgs && msgs.length) {
          this.messages = msgs.map(m => ({
            id: m.id || generateId(),
            role: m.role === 'user' ? 'user' : 'bot',
            content: m.content || '',
            sources: m.metadata?.sources || [],
            time: m.created_at ? this._fmt(m.created_at) : formatTime()
          }))
          this.$nextTick(() => this.scrollToBottom())
        }
      } catch(e) {
        // 会话不存在或没有消息，正常开始新对话
        console.log('No history messages:', e.message)
      }
    },

    _fmt(isoStr) {
      if (!isoStr) return formatTime()
      const d = new Date(isoStr)
      if (isNaN(d.getTime())) return formatTime()
      return String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0')
    },

    loadHistory() {
      // 加载更早的历史（暂不实现，后续可加）
    },

    // ── 发送消息 ──
    async sendMessage() {
      const text = this.inputText.trim()
      if (!text || this.loading) return

      this.inputText = ''
      this.loading = true
      this.statusText = '思考中...'

      // 添加用户消息
      const userMsg = {
        id: generateId(),
        role: 'user',
        content: text,
        time: formatTime()
      }
      this.messages.push(userMsg)

      // 保存会话（首次发送时）
      if (this.messages.length === 1) {
        try {
          const token = uni.getStorageSync('ai_token') || uni.getStorageSync('token') || ''
          await createSession(this.sessionId, text.slice(0, 50), token ? 'user' : 'anon')
          uni.setStorageSync('ai_last_session', this.sessionId)
        } catch(e) {
          console.log('Create session failed:', e.message)
        }
      }

      this.scrollToBottom()

      // 调用后端 API
      try {
        const hint = this.pendingIntent
        this.pendingIntent = null
        const result = await apiSendMessage(this.sessionId, text, hint)

        const botMsg = {
          id: generateId(),
          role: 'bot',
          content: result.answer || '抱歉，我没有理解您的问题，请换个方式描述。',
          sources: result.sources || [],
          time: formatTime()
        }
        this.messages.push(botMsg)
        this.statusText = '在线'
      } catch(e) {
        console.error('Chat error:', e)
        const errMsg = e.message.includes('Unauthorized')
          ? '登录已过期，请重新登录后使用'
          : '网络开小差了，请稍后再试'
        this.messages.push({
          id: generateId(),
          role: 'bot',
          content: '😅 ' + errMsg,
          sources: [],
          time: formatTime()
        })
        this.statusText = '连接失败'
      }

      this.loading = false
      this.$nextTick(() => this.scrollToBottom())
    },

    // ── 辅助 ──
    scrollToBottom() {
      this.$nextTick(() => {
        const el = this.$refs?.msgList?.$el || this.$refs?.msgList
        if (el) el.scrollTop = el.scrollHeight
      })
    },

    onInput(e) {
      // 可加输入限制
    },

    // ── Markdown 转 HTML（供 rich-text 使用） ──
    renderMarkdown(text) {
      if (!text) return ''
      let h = this._escapeHtml(text)

      // 代码块
      const blocks = []
      h = h.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        const i = blocks.length
        blocks.push('<pre><code>' + this._escapeHtml(code.trim()) + '</code></pre>')
        return `%%CB${i}%%`
      })

      // 行内代码
      h = h.replace(/`([^`]+)`/g, '<code>$1</code>')

      // 标题
      h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>')
      h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>')
      h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>')

      // 粗斜体
      h = h.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
      h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      h = h.replace(/\*(.+?)\*/g, '<em>$1</em>')

      // 图片
      h = h.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<image src="$2" alt="$1" style="max-width:100%" mode="widthFix"></image>')

      // 链接
      h = h.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')

      // 列表
      h = h.replace(/^[-*] (.+)$/gm, '<li>$1</li>')
      h = h.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
      h = h.replace(/^\d+\. (.+)$/gm, '<li>$1</li>')

      // 换行
      h = h.replace(/\n/g, '<br/>')

      // 恢复代码块
      h = h.replace(/%%CB(\d+)%%/g, (_, i) => blocks[i] || '')

      return h
    },

    _escapeHtml(t) {
      return String(t)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
    }
  }
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: #f5f6f8;
  font-family: -apple-system, 'Helvetica Neue', sans-serif;
}
/* 确保子元素不溢出 */
.chat-page > view {
  flex-shrink: 0;
}

/* ── 导航栏 ── */
.nav-bar {
  display: flex;
  align-items: center;
  padding: 60rpx 0 20rpx;
  background: #fff;
  border-bottom: 1rpx solid #e8e8e8;
  flex-shrink: 0;
}
.nav-back {
  width: 100rpx;
  height: 60rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.nav-left {
  display: flex;
  align-items: center;
  gap: 12rpx;
  width: 130rpx;
  flex-shrink: 0;
}
.nav-back-icon {
  font-size: 36rpx;
  color: #333;
  padding: 10rpx;
}
.nav-hist-btn {
  font-size: 34rpx;
  padding: 10rpx;
}
.nav-info {
  flex: 1;
  text-align: center;
}
.nav-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #1a1a2e;
}
.nav-subtitle {
  font-size: 22rpx;
  color: #999;
  margin-top: 4rpx;
}
.nav-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  width: 130rpx;
  flex-shrink: 0;
}
.nav-new-btn {
  font-size: 40rpx;
  font-weight: 300;
  color: #666;
  padding: 10rpx 16rpx;
}

/* ── 消息列表 ── */
.msg-list {
  flex: 1;
  overflow-y: scroll;
  overflow-x: hidden;
  padding: 20rpx 24rpx 0;
  -webkit-overflow-scrolling: touch;
}

/* ── 提示词列表 ── */
.prompts-wrap {
  padding: 40rpx 28rpx 40rpx;
}
.prompts-tabs {
  display: flex;
  gap: 12rpx;
  margin-bottom: 20rpx;
}
.prompts-tab {
  font-size: 24rpx;
  color: #666;
  padding: 12rpx 24rpx;
  border-radius: 30rpx;
  background: #f0f2f5;
  line-height: 1;
}
.prompts-tab-active {
  background: #0f3460;
  color: #fff;
  font-weight: 500;
}
.prompts-title {
  display: block;
  font-size: 28rpx;
  color: #666;
  margin-bottom: 28rpx;
  font-weight: 500;
}
.prompt-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 26rpx 24rpx;
  margin-bottom: 16rpx;
  background: #fff;
  border-radius: 14rpx;
  border: 2rpx solid #e8e8e8;
}
.prompt-item:active {
  background: #f5f6f8;
  border-color: #0f3460;
}
.prompt-text {
  font-size: 26rpx;
  color: #333;
  flex: 1;
  padding-right: 16rpx;
  line-height: 1.4;
}
.prompt-arrow {
  font-size: 24rpx;
  color: #ccc;
  flex-shrink: 0;
}
.prompts-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24rpx;
  margin-top: 32rpx;
}
.prompts-page {
  font-size: 24rpx;
  color: #bbb;
}
.prompts-next {
  font-size: 26rpx;
  color: #0f3460;
  padding: 8rpx 20rpx;
  border: 2rpx solid #0f3460;
  border-radius: 30rpx;
}
.prompts-next:active {
  background: #0f3460;
  color: #fff;
}

.msg-item {
  display: flex;
  gap: 16rpx;
  margin-bottom: 28rpx;
  animation: fadeIn 0.3s ease;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(16rpx); }
  to { opacity: 1; transform: translateY(0); }
}

.msg-user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 56rpx;
  height: 56rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  flex-shrink: 0;
}
.msg-user .msg-avatar {
  background: #e94560;
}
.msg-bot .msg-avatar {
  background: #0f3460;
}

.msg-content {
  max-width: 75%;
}

.msg-bubble {
  padding: 18rpx 22rpx;
  border-radius: 16rpx;
  font-size: 28rpx;
  line-height: 1.7;
  word-break: break-word;
}
.msg-user .msg-bubble {
  background: #e94560;
  color: #fff;
  border-bottom-right-radius: 6rpx;
}
.msg-bot .msg-bubble {
  background: #fff;
  color: #333;
  border-bottom-left-radius: 6rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,.06);
}
.msg-bot .rich-text {
  font-size: 28rpx;
  line-height: 1.7;
}
.user-text {
  font-size: 28rpx;
  line-height: 1.5;
  white-space: pre-wrap;
}

/* rich-text 内部样式 */
.rich-text >>> h1, .rich-text >>> h2, .rich-text >>> h3 {
  font-weight: 600;
  margin: 12rpx 0 6rpx;
}
.rich-text >>> h1 { font-size: 34rpx; }
.rich-text >>> h2 { font-size: 32rpx; }
.rich-text >>> h3 { font-size: 30rpx; }
.rich-text >>> p { margin: 4rpx 0; }
.rich-text >>> ul, .rich-text >>> ol {
  padding-left: 32rpx;
  margin: 4rpx 0;
}
.rich-text >>> code {
  background: #f0f2f5;
  padding: 2rpx 10rpx;
  border-radius: 6rpx;
  font-size: 24rpx;
}
.rich-text >>> pre {
  background: #1a1a2e;
  color: #e6e6e6;
  padding: 20rpx;
  border-radius: 12rpx;
  overflow-x: auto;
  margin: 8rpx 0;
}
.rich-text >>> pre code {
  background: none;
  padding: 0;
  color: inherit;
  font-size: 24rpx;
}
.rich-text >>> image {
  max-width: 100%;
  border-radius: 8rpx;
  margin: 8rpx 0;
}

.msg-time {
  font-size: 20rpx;
  color: #bbb;
  margin-top: 6rpx;
  padding: 0 4rpx;
}
.msg-user .msg-time {
  text-align: right;
}

/* 来源引用 */
.msg-sources {
  margin-top: 12rpx;
  padding-top: 12rpx;
  border-top: 2rpx solid rgba(0,0,0,.06);
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
}
.msg-user .msg-sources {
  border-top-color: rgba(255,255,255,.2);
}
.source-item {
  display: inline-flex;
  align-items: center;
  background: rgba(0,0,0,.04);
  border-radius: 6rpx;
  padding: 4rpx 12rpx;
  font-size: 22rpx;
}
.msg-user .source-item {
  background: rgba(255,255,255,.15);
}
.source-icon {
  margin-right: 4rpx;
}
.source-name {
  color: inherit;
  opacity: .8;
}

/* 思考中动画 */
.thinking-bubble {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.thinking-dots {
  display: flex;
  gap: 6rpx;
}
.dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background: #bbb;
  animation: dotPulse 1.4s infinite;
}
.dot:nth-child(2) { animation-delay: .2s; }
.dot:nth-child(3) { animation-delay: .4s; }
@keyframes dotPulse {
  0%, 60%, 100% { opacity: .3; transform: scale(.8); }
  30% { opacity: 1; transform: scale(1); }
}
.thinking-text {
  font-size: 24rpx;
  color: #999;
}

/* ── 输入区 ── */
.input-area {
  padding: 16rpx 24rpx;
  background: #fff;
  border-top: 1rpx solid #e8e8e8;
  flex-shrink: 0;
}
.input-safe {
  padding-bottom: 40rpx;
}
.input-wrapper {
  display: flex;
  align-items: center;
  gap: 16rpx;
}
.input-box {
  flex: 1;
  height: 72rpx;
  border: 2rpx solid #d9d9d9;
  border-radius: 36rpx;
  padding: 0 28rpx;
  font-size: 28rpx;
  background: #f5f6f8;
  outline: none;
}
.input-box:focus {
  border-color: #0f3460;
  background: #fff;
}
.input-box[disabled] {
  background: #eee;
  color: #999;
}
.send-btn {
  height: 72rpx;
  min-width: 120rpx;
  border-radius: 36rpx;
  background: #0f3460;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: 0 24rpx;
}
.send-btn-disabled {
  opacity: .35;
}
.send-icon {
  color: #fff;
  font-size: 28rpx;
  font-weight: 500;
}

/* ── 历史记录面板 ── */
.hist-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,.35);
  z-index: 1999;
}
.hist-panel {
  position: fixed;
  top: 0; left: 0; bottom: 0;
  width: 520rpx;
  background: #fff;
  z-index: 2000;
  transform: translateX(-100%);
  transition: transform .25s ease;
  display: flex;
  flex-direction: column;
}
.hist-open {
  transform: translateX(0);
}
.hist-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 88rpx 28rpx 24rpx;
  border-bottom: 1rpx solid #e8e8e8;
  flex-shrink: 0;
}
.hist-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #1a1a2e;
}
.hist-close {
  font-size: 32rpx;
  color: #999;
  padding: 10rpx;
}
.hist-list {
  flex: 1;
  overflow-y: auto;
  padding: 16rpx 0 40rpx;
}
.hist-group {
  margin-bottom: 12rpx;
}
.hist-group-label {
  display: block;
  font-size: 24rpx;
  color: #999;
  padding: 16rpx 28rpx 8rpx;
  font-weight: 500;
}
.hist-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20rpx 28rpx;
  border-bottom: 1rpx solid #f5f5f5;
}
.hist-item:active {
  background: #f5f6f8;
}
.hist-item-title {
  font-size: 26rpx;
  color: #333;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 16rpx;
}
.hist-item-time {
  font-size: 22rpx;
  color: #bbb;
  flex-shrink: 0;
}
.hist-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-top: 200rpx;
  font-size: 26rpx;
  color: #bbb;
}
</style>
