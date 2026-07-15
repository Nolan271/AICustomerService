<template>
  <view class="page">
    <!-- ====== 页面原有内容 ====== -->
    <!-- 这里是你首页原有的内容，只加了一个浮动按钮 -->

    <!-- 占位演示内容 -->
    <view class="placeholder">
      <text class="placeholder-title">充电桩管理平台</text>
      <text class="placeholder-desc">你的小程序首页内容</text>
    </view>

    <!-- ====== AI 客服浮动按钮 ====== -->
    <view class="ai-float-btn" @click="goChat" hover-class="ai-float-btn-hover">
      <text class="ai-float-icon">🤖</text>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {}
  },
  methods: {
    goChat() {
      uni.navigateTo({ url: '/pages/chat/index' })
    }
  }
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  position: relative;
}

/* ── 你的首页原有样式 ── */
.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 200rpx;
}
.placeholder-title {
  font-size: 36rpx;
  font-weight: 600;
  color: #333;
}
.placeholder-desc {
  font-size: 28rpx;
  color: #999;
  margin-top: 16rpx;
}

/* ── AI 浮标按钮 ── */
.ai-float-btn {
  position: fixed;
  right: 32rpx;
  bottom: 120rpx;
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #0f3460, #1a5276);
  box-shadow: 0 8rpx 24rpx rgba(15, 52, 96, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
  transition: transform 0.2s;
}
.ai-float-btn-hover {
  transform: scale(0.92);
}
.ai-float-icon {
  font-size: 44rpx;
  line-height: 1;
}
</style>
