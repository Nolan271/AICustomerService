<template>
  <view>
    <view class="hist-overlay" v-if="visible" @click="$emit('close')"></view>
    <view class="hist-panel" :class="{ 'hist-open': visible }">
      <view class="hist-header">
        <text class="hist-title">历史对话</text>
        <text class="hist-close" @click="$emit('close')">✕</text>
      </view>
      <scroll-view class="hist-list" scroll-y>
        <view v-if="sessions.today.length" class="hist-group">
          <text class="hist-group-label">今天</text>
          <view v-for="s in sessions.today" :key="s.id" class="hist-item" @click="$emit('loadSession', s)">
            <text class="hist-item-title">{{ s.title || '新对话' }}</text>
            <text class="hist-item-time">{{ fmtTime(s.updated_at || s.created_at) }}</text>
          </view>
        </view>
        <view v-if="sessions.yesterday.length" class="hist-group">
          <text class="hist-group-label">昨天</text>
          <view v-for="s in sessions.yesterday" :key="s.id" class="hist-item" @click="$emit('loadSession', s)">
            <text class="hist-item-title">{{ s.title || '新对话' }}</text>
            <text class="hist-item-time">{{ fmtTime(s.updated_at || s.created_at) }}</text>
          </view>
        </view>
        <view v-if="sessions.week.length" class="hist-group">
          <text class="hist-group-label">近7天</text>
          <view v-for="s in sessions.week" :key="s.id" class="hist-item" @click="$emit('loadSession', s)">
            <text class="hist-item-title">{{ s.title || '新对话' }}</text>
            <text class="hist-item-time">{{ fmtTime(s.updated_at || s.created_at) }}</text>
          </view>
        </view>
        <view v-if="!sessions.today.length && !sessions.yesterday.length && !sessions.week.length" class="hist-empty">
          <text>暂无历史记录</text>
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script>
export default {
  props: { visible: Boolean, sessions: Object },
  emits: ['close', 'loadSession'],
  methods: {
    fmtTime(iso) {
      if (!iso) return ''
      const d = new Date(iso)
      if (isNaN(d.getTime())) return ''
      return String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0')
    }
  }
}
</script>

<style scoped>
.hist-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,.35); z-index: 1999; }
.hist-panel { position: fixed; top: 0; left: 0; bottom: 0; width: 520rpx; background: #fff; z-index: 2000; transform: translateX(-100%); transition: transform .25s ease; display: flex; flex-direction: column; }
.hist-open { transform: translateX(0); }
.hist-header { display: flex; align-items: center; justify-content: space-between; padding: 88rpx 28rpx 24rpx; border-bottom: 1rpx solid #e8e8e8; flex-shrink: 0; }
.hist-title { font-size: 32rpx; font-weight: 600; color: #1a1a2e; }
.hist-close { font-size: 32rpx; color: #999; padding: 10rpx; }
.hist-list { flex: 1; overflow-y: auto; padding: 16rpx 0 40rpx; }
.hist-group { margin-bottom: 12rpx; }
.hist-group-label { display: block; font-size: 24rpx; color: #999; padding: 16rpx 28rpx 8rpx; font-weight: 500; }
.hist-item { display: flex; align-items: center; justify-content: space-between; padding: 20rpx 28rpx; border-bottom: 1rpx solid #f5f5f5; }
.hist-item:active { background: #f5f6f8; }
.hist-item-title { font-size: 26rpx; color: #333; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-right: 16rpx; }
.hist-item-time { font-size: 22rpx; color: #bbb; flex-shrink: 0; }
.hist-empty { display: flex; align-items: center; justify-content: center; padding-top: 200rpx; font-size: 26rpx; color: #bbb; }
</style>
