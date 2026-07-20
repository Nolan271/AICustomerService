<template>
  <view class="chat-page">
    <chat-header :statusText="statusText" @back="goBack" @toggleHistory="toggleHistory" @newChat="newChat" />
    <chat-history :visible="showHistory" :sessions="groupedSessions" @close="closeHistory" @loadSession="loadSession" />

    <view class="msg-list" id="msg-list" ref="msgList">
      <chat-prompts
        :tabs="promptTabs" :activeTab="promptTab" :items="currentPrompts"
        :page="promptPage" :totalPages="totalPromptPages"
        @tabChange="promptTab = $event" @send="sendPrompt" @next="nextPrompts" />

      <chat-message v-for="msg in messages" :key="msg.id" :message="msg" :imgBaseUrl="imgBaseUrl" />

      <view v-if="loading" class="msg-item msg-bot">
        <view class="msg-content">
          <view class="msg-bubble thinking-bubble">
            <view class="thinking-dots"><view class="dot"></view><view class="dot"></view><view class="dot"></view></view>
            <text class="thinking-text">思考中...</text>
          </view>
        </view>
      </view>
      <view style="height:20rpx"></view>
    </view>

    <chat-input :text="inputText" :disabled="loading" @send="sendMessage" @update:text="inputText = $event" />
  </view>
</template>

<script>
import ChatHeader from '@/components/chat-header.vue'
import ChatHistory from '@/components/chat-history.vue'
import ChatPrompts from '@/components/chat-prompts.vue'
import ChatMessage from '@/components/chat-message.vue'
import ChatInput from '@/components/chat-input.vue'
import { sendMessage as apiSendMessage, createSession, getSessionMessages, getSessions, getPrompts } from '@/utils/ai-api.js'

function generateId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 8) }
function formatTime() { const d = new Date(); return String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0') }

export default {
  components: { ChatHeader, ChatHistory, ChatPrompts, ChatMessage, ChatInput },
  data() {
    return {
      sessionId: '', messages: [], inputText: '', loading: false, statusText: '在线',
      showHistory: false, sessions: [], groupedSessions: { today: [], yesterday: [], week: [] },
      promptTab: 'all', promptPage: 1, pendingIntent: null,
      imgBaseUrl: (import.meta.env.VITE_SERVER_BASE || 'http://3d0e7225.r10.cpolar.top'),
      promptTabs: [{ key: 'all', label: '全部' }], promptMap: {}, allPrompts: []
    }
  },
  computed: {
    filteredPrompts() {
      if (this.promptTab === 'all') return this.allPrompts
      return this.promptMap[this.promptTab] || []
    },
    currentPrompts() { const s = (this.promptPage - 1) * 5; return this.filteredPrompts.slice(s, s + 5) },
    totalPromptPages() { return Math.ceil(this.filteredPrompts.length / 5) }
  },
  onLoad() { this.initSession(); this.checkDevice(); this.loadPrompts() },
  methods: {
    initSession() {
      const last = uni.getStorageSync('ai_last_session') || ''
      if (last) { this.sessionId = last; this.loadMessages(last) }
      else this.sessionId = generateId()
    },
    checkDevice() {
      try { const info = uni.getSystemInfoSync(); this.isIphoneX = info.safeArea && info.safeArea.bottom < info.windowHeight } catch(e) {}
    },
    goBack() { uni.navigateBack() },
    newChat() { this.sessionId = generateId(); this.messages = []; this.inputText = ''; uni.setStorageSync('ai_last_session', this.sessionId) },

    async loadPrompts() {
      try { const d = await getPrompts(); if (d && d.tabs) this.promptTabs = d.tabs; if (d && d.prompts) { this.promptMap = d.prompts; const flat = []; for (const cat of Object.keys(d.prompts)) for (const item of d.prompts[cat]) flat.push({...item, cat}); this.allPrompts = flat } }
      catch(e) { console.log('加载提示词失败:', e.message) }
    },

    sendPrompt(text, intent) { this.inputText = text; this.pendingIntent = intent; this.sendMessage() },
    nextPrompts() { this.promptPage = this.promptPage < this.totalPromptPages ? this.promptPage + 1 : 1 },

    toggleHistory() { this.showHistory = !this.showHistory; if (this.showHistory) this.fetchSessions() },
    closeHistory() { this.showHistory = false },

    async fetchSessions() { try { const d = await getSessions(); this.sessions = d.items || []; this.groupSessions() } catch(e) {} },
    groupSessions() {
      const g = { today: [], yesterday: [], week: [] }; const n = new Date()
      this.sessions.forEach(s => {
        const d = new Date(s.updated_at || s.created_at)
        if (d.toDateString() === n.toDateString()) g.today.push(s)
        else if (d.toDateString() === new Date(n - 864e5).toDateString()) g.yesterday.push(s)
        else if (d >= new Date(n - 7*864e5)) g.week.push(s)
      })
      this.groupedSessions = g
    },
    async loadSession(session) {
      this.closeHistory(); this.sessionId = session.id; uni.setStorageSync('ai_last_session', session.id); this.messages = []; await this.loadMessages(session.id); this.scrollToBottom()
    },

    async loadMessages(sessionId) {
      try {
        const msgs = await getSessionMessages(sessionId)
        if (msgs && msgs.length) {
          this.messages = msgs.map(m => ({ id: m.id || generateId(), role: m.role === 'user' ? 'user' : 'bot', content: m.content || '', sources: m.metadata?.sources || [], chartConfig: m.metadata?.chart_config || null, time: m.created_at ? this._fmt(m.created_at) : formatTime() }))
          this.$nextTick(() => { this.scrollToBottom(); setTimeout(() => { this.messages.forEach(msg => { if (msg.chartConfig) this.drawChart(msg.id, msg.chartConfig) }) }, 800) })
        }
      } catch(e) { console.log('No history messages:', e.message) }
    },
    _fmt(iso) { if (!iso) return formatTime(); const d = new Date(iso); return isNaN(d.getTime()) ? formatTime() : String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0') },

    async sendMessage() {
      const text = this.inputText.trim()
      if (!text || this.loading) return
      this.inputText = ''; this.loading = true; this.statusText = '思考中...'
      this.messages.push({ id: generateId(), role: 'user', content: text, time: formatTime() })

      if (this.messages.length === 1) {
        try { await createSession(this.sessionId, text.slice(0, 50), 'anon'); uni.setStorageSync('ai_last_session', this.sessionId) } catch(e) {}
      }
      this.scrollToBottom()

      try {
        const hint = this.pendingIntent; this.pendingIntent = null
        const result = await apiSendMessage(this.sessionId, text, hint)
        this.messages.push({ id: generateId(), role: 'bot', content: result.answer || '', sources: result.sources || [], chartConfig: result.chart_config || null, time: formatTime() })
        this.statusText = '在线'
      } catch(e) {
        const msg = e.message.includes('Unauthorized') ? '登录已过期，请重新登录后使用' : '网络开小差了，请稍后再试'
        this.messages.push({ id: generateId(), role: 'bot', content: '😅 ' + msg, sources: [], chartConfig: null, time: formatTime() })
        this.statusText = '连接失败'
      }
      this.loading = false; this.$nextTick(() => this.scrollToBottom())
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const el = this.$refs?.msgList?.$el || this.$refs?.msgList; if (el) el.scrollTop = el.scrollHeight
        this.messages.forEach(m => { if (m.chartConfig && m.role === 'bot') setTimeout(() => this.drawChart(m.id, m.chartConfig), 500) })
      })
    },

    drawChart(id, config) {
      if (!config || !config.keys || !config.values) return
      // 日期格式统一为 MM/DD
      const fmtKeys = config.keys.map(k => k.length === 10 ? k.slice(5, 7) + '/' + k.slice(8, 10) : k)
      if (typeof window !== 'undefined' && document) {
        this.$nextTick(() => { setTimeout(() => {
          const dom = document.getElementById('chart-' + id)
          if (!dom || !window.echarts) return
          dom.style.width = '100%'; dom.style.height = '360rpx'
          const chart = window.echarts.init(dom)
          chart.setOption({ tooltip: { trigger: 'axis' }, grid: { left: '12%', right: '5%', bottom: '18%', top: '12%' }, xAxis: { type: 'category', data: fmtKeys, axisLabel: { rotate: 0, fontSize: 11 } }, yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed', color: '#eee' } } }, series: [{ type: 'line', data: config.values.map(Number), smooth: true, lineStyle: { width: 2, color: '#667eea' }, areaStyle: { color: 'rgba(102,126,234,0.12)' }, symbol: 'circle', symbolSize: 6, itemStyle: { color: '#667eea' } }] })
        }, 600) })
        return
      }
      const cid = 'chart-' + id, sys = uni.getSystemInfoSync(), dpr = sys.pixelRatio || 2
      const cw = 690, ch = 360, pad = { top: 30, right: 24, bottom: 50, left: 60 }
      const pw = cw - pad.left - pad.right, ph = ch - pad.top - pad.bottom
      const ks = fmtKeys, vs = config.values.map(Number), mv = Math.max(...vs, 0.1), cl = '#667eea'
      const cx = uni.createCanvasContext(cid, this)
      cx.scale(dpr, dpr); cx.setFillStyle('#f8f9ff'); cx.fillRect(0,0,cw,ch)
      cx.setStrokeStyle('#e8e8e8'); cx.setLineWidth(1)
      for (let i=0;i<=4;i++){const y=pad.top+(ph/4)*i;cx.beginPath();cx.moveTo(pad.left,y);cx.lineTo(cw-pad.right,y);cx.stroke()}
      cx.setFontSize(11);cx.setFillStyle('#999');cx.setTextAlign('right')
      for(let i=0;i<=4;i++)cx.fillText(String(Math.round(mv-(mv/4)*i)),pad.left-8,pad.top+(ph/4)*i+4)
      const sx=pw/Math.max(ks.length-1,1),pts=vs.map((v,i)=>({x:pad.left+sx*i,y:pad.top+ph-(v/mv)*ph}))
      cx.beginPath();cx.moveTo(pts[0].x,pad.top+ph);pts.forEach(p=>cx.lineTo(p.x,p.y));cx.lineTo(pts[pts.length-1].x,pad.top+ph);cx.closePath()
      cx.setFillStyle('rgba(102,126,234,0.15)');cx.fill()
      cx.beginPath();cx.setStrokeStyle(cl);cx.setLineWidth(3);cx.setLineJoin('round')
      pts.forEach((p,i)=>i===0?cx.moveTo(p.x,p.y):cx.lineTo(p.x,p.y));cx.stroke()
      pts.forEach(p=>{cx.beginPath();cx.arc(p.x,p.y,5,0,Math.PI*2);cx.setFillStyle('#fff');cx.fill();cx.setStrokeStyle(cl);cx.setLineWidth(2);cx.stroke()})
      cx.setFontSize(10);cx.setFillStyle('#999');cx.setTextAlign('center')
      const ls=Math.max(1,Math.floor(ks.length/6));ks.forEach((k,i)=>{if(i===0||i%ls===0||i===ks.length-1)cx.fillText(k,pts[i].x,pad.top+ph+28)})
      cx.setFontSize(12);cx.setFillStyle('#333');cx.setTextAlign('left');cx.fillText(config.title||'',pad.left,20);cx.draw()
    }
  }
}
</script>

<style>
.chat-page { display: flex; flex-direction: column; height: 100vh; overflow: hidden; background: #f0f2f5; }
.chat-page > view { flex-shrink: 0; }
.msg-list { flex: 1; overflow-y: scroll; overflow-x: hidden; padding: 24rpx 28rpx 0; -webkit-overflow-scrolling: touch; }
.thinking-bubble { display: flex; align-items: center; gap: 12rpx; }
.thinking-dots { display: flex; gap: 6rpx; }
.dot { width: 14rpx; height: 14rpx; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2); animation: dotPulse 1.4s infinite; }
.dot:nth-child(2) { animation-delay: .2s; }
.dot:nth-child(3) { animation-delay: .4s; }
@keyframes dotPulse { 0%,60%,100% { opacity:.3; transform:scale(.8) } 30% { opacity:1; transform:scale(1) } }
.thinking-text { font-size: 24rpx; color: #667eea; }
</style>
