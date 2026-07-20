<template>
  <view class="msg-item" :class="message.role === 'user' ? 'msg-user' : 'msg-bot'">

    <view class="msg-content">
      <view class="msg-bubble">
        <rich-text v-if="message.role === 'bot'" :nodes="renderMarkdown(message.content)" class="rich-text"></rich-text>
        <text v-else class="user-text">{{ message.content }}</text>
        <canvas v-if="message.chartConfig" :id="'chart-' + message.id" :canvas-id="'chart-' + message.id" class="msg-chart"></canvas>
        <view v-if="message.sources && message.sources.length" class="msg-sources">
          <view v-for="(src, si) in filteredSources" :key="si" class="source-item">
            <text class="source-icon">📄</text><text class="source-name">{{ src.doc_name }}</text>
          </view>
        </view>
      </view>
      <text class="msg-time">{{ message.time }}</text>
    </view>
  </view>
</template>

<script>
export default {
  props: { message: Object, imgBaseUrl: String },
  computed: {
    filteredSources() {
      return (this.message.sources || []).filter(s => s.doc_name && !s.doc_name.startsWith('API:'))
    }
  },
  methods: {
    renderMarkdown(text) {
      if (!text) return ''
      let h = this._escapeHtml(text)
      const blocks = []
      h = h.replace(/```(\w*)\n([\s\S]*?)```/g, (_, l, c) => { const i = blocks.length; blocks.push('<pre><code>' + this._escapeHtml(c.trim()) + '</code></pre>'); return `%%CB${i}%%` })
      h = h.replace(/`([^`]+)`/g, '<code>$1</code>')
      h = h.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (m, alt, src) => '<img src="' + (src.startsWith('/') ? this.imgBaseUrl + src : src) + '" alt="' + alt + '" style="max-width:100%;border-radius:8rpx;margin:8rpx 0" />')
      h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>').replace(/^## (.+)$/gm, '<h2>$1</h2>').replace(/^# (.+)$/gm, '<h1>$1</h1>')
      h = h.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\*(.+?)\*/g, '<em>$1</em>')
      h = h.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
      h = h.replace(/^[-*] (.+)$/gm, '<li>$1</li>').replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>').replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
      h = h.replace(/\n/g, '<br/>')
      h = h.replace(/%%CB(\d+)%%/g, (_, i) => blocks[i] || '')
      return h
    },
    _escapeHtml(t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') }
  }
}
</script>

<style scoped>
.msg-item { display: flex; gap: 16rpx; margin-bottom: 32rpx; animation: fadeIn .3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(20rpx); } to { opacity: 1; transform: translateY(0); } }
.msg-user { flex-direction: row-reverse; }
.msg-content { max-width: 76%; }
.msg-bubble { padding: 20rpx 24rpx; border-radius: 20rpx; font-size: 28rpx; line-height: 1.7; word-break: break-word; }
.msg-user .msg-bubble { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; border-bottom-right-radius: 4rpx; box-shadow: 0 4rpx 12rpx rgba(102,126,234,.25); }
.msg-bot .msg-bubble { background: #fff; color: #333; border-bottom-left-radius: 4rpx; box-shadow: 0 2rpx 10rpx rgba(0,0,0,.05); }
.user-text { font-size: 28rpx; line-height: 1.5; white-space: pre-wrap; }
.msg-time { font-size: 20rpx; color: #bbb; margin-top: 6rpx; padding: 0 4rpx; }
.msg-user .msg-time { text-align: right; }
.msg-chart { width: 100%; height: 360rpx; margin: 16rpx 0; border-radius: 16rpx; background: #f8f9ff; }
.msg-sources { margin-top: 12rpx; padding-top: 12rpx; border-top: 2rpx solid rgba(0,0,0,.06); display: flex; flex-wrap: wrap; gap: 8rpx; }
.msg-user .msg-sources { border-top-color: rgba(255,255,255,.2); }
.source-item { display: inline-flex; align-items: center; background: rgba(0,0,0,.04); border-radius: 6rpx; padding: 4rpx 12rpx; font-size: 22rpx; }
.msg-user .source-item { background: rgba(255,255,255,.15); }
.source-icon { margin-right: 4rpx; }
.source-name { color: inherit; opacity: .8; }
.rich-text >>> h1, .rich-text >>> h2, .rich-text >>> h3 { font-weight: 600; margin: 12rpx 0 6rpx; }
.rich-text >>> h1 { font-size: 34rpx; } .rich-text >>> h2 { font-size: 32rpx; } .rich-text >>> h3 { font-size: 30rpx; }
.rich-text >>> p { margin: 4rpx 0; }
.rich-text >>> ul, .rich-text >>> ol { padding-left: 32rpx; margin: 4rpx 0; }
.rich-text >>> code { background: #f0f2f5; padding: 2rpx 10rpx; border-radius: 6rpx; font-size: 24rpx; }
.rich-text >>> pre { background: #1a1a2e; color: #e6e6e6; padding: 20rpx; border-radius: 12rpx; overflow-x: auto; margin: 8rpx 0; }
.rich-text >>> pre code { background: none; padding: 0; color: inherit; font-size: 24rpx; }
.rich-text >>> img { max-width: 100%; border-radius: 8rpx; margin: 8rpx 0; }
</style>
