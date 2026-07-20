<template>
  <view class="nav-bar">
    <view class="nav-left">
      <text class="nav-back-icon" @click="$emit('back')">←</text>
      <text class="nav-hist-btn" @click="$emit('toggleHistory')">📋</text>
    </view>
    <view class="nav-info">
      <text class="nav-subtitle">{{ statusText }}</text>
      <text class="nav-title">AI 运营助手</text>
    </view>
    <view class="nav-right">
      <text class="nav-new-btn" @click="$emit('newChat')">✚</text>
    </view>
  </view>
</template>

<script>
export default {
  props: { statusText: { type: String, default: '在线' } },
  emits: ['back', 'toggleHistory', 'newChat']
}
</script>

<style scoped>
.nav-bar {
  display: flex; align-items: center;
  padding: 150rpx 0 36rpx;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  flex-shrink: 0;
}
.nav-left { display: flex; align-items: center; gap: 8rpx; width: 140rpx; flex-shrink: 0; padding-left: 20rpx; }
.nav-back-icon { font-size: 36rpx; color: rgba(255,255,255,.9); padding: 8rpx; }
.nav-hist-btn { font-size: 34rpx; padding: 8rpx; color: rgba(255,255,255,.85); }
.nav-info { flex: 1; text-align: center; position: relative; height: 44rpx; display: flex; align-items: center; justify-content: center; }
.nav-title { font-size: 34rpx; font-weight: 700; color: #fff; letter-spacing: 2rpx; line-height: 44rpx; }
.nav-subtitle { font-size: 18rpx; color: rgba(255,255,255,.6); position: absolute; top: -32rpx; left: 0; right: 0; text-align: center; }
.nav-right { display: flex; align-items: center; justify-content: flex-end; width: 140rpx; flex-shrink: 0; padding-right: 20rpx; }
.nav-new-btn { font-size: 38rpx; font-weight: 300; color: rgba(255,255,255,.9); padding: 8rpx 16rpx; }
</style>
