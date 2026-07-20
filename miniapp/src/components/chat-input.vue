<template>
  <view class="input-area">
    <view class="input-wrapper">
      <input class="input-box" :value="text" type="text"
        :placeholder="disabled ? '请等待回复...' : '输入您的问题...'"
        :disabled="disabled" confirm-type="send" @confirm="send" @input="$emit('update:text', $event.detail.value)" />
      <view class="send-btn" :class="{ 'send-btn-disabled': !text.trim() || disabled }" @click="send">
        <text class="send-icon">发送</text>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  props: { text: String, disabled: Boolean },
  emits: ['send', 'update:text'],
  methods: {
    send() { if (this.text.trim() && !this.disabled) this.$emit('send') }
  }
}
</script>

<style scoped>
.input-area { padding: 16rpx 24rpx; background: #fff; border-top: 1rpx solid #e8e8e8; flex-shrink: 0; }
.input-wrapper { display: flex; align-items: center; gap: 16rpx; }
.input-box { flex: 1; height: 72rpx; border: 2rpx solid #d9d9d9; border-radius: 36rpx; padding: 0 28rpx; font-size: 28rpx; background: #f5f6f8; outline: none; }
.input-box:focus { border-color: #667eea; background: #fff; box-shadow: 0 0 0 4rpx rgba(102,126,234,.1); }
.send-btn { height: 72rpx; min-width: 120rpx; border-radius: 36rpx; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; flex-shrink: 0; padding: 0 24rpx; box-shadow: 0 4rpx 12rpx rgba(102,126,234,.3); }
.send-btn-disabled { opacity: .35; }
.send-icon { color: #fff; font-size: 28rpx; font-weight: 500; }
</style>
