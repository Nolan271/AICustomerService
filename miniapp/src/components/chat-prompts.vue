<template>
  <view class="prompts-wrap">
    <view class="prompts-tabs">
      <text v-for="tab in tabs" :key="tab.key" class="prompts-tab"
        :class="{ 'prompts-tab-active': activeTab === tab.key }"
        @click="$emit('tabChange', tab.key)">{{ tab.label }}</text>
    </view>
    <text class="prompts-title">💡 我可以帮你解决使用方面的相关问题</text>
    <view v-for="(item, idx) in items" :key="idx" class="prompt-item" @click="$emit('send', item.text, item.intent || 'KB_QA')">
      <text class="prompt-text">{{ item.text }}</text>
      <text class="prompt-arrow">➤</text>
    </view>
    <view class="prompts-footer">
      <text class="prompts-page">{{ page }}/{{ totalPages }}</text>
      <text class="prompts-next" @click="$emit('next')">换一批 →</text>
    </view>
  </view>
</template>

<script>
export default {
  props: { tabs: Array, activeTab: String, items: Array, page: Number, totalPages: Number },
  emits: ['tabChange', 'send', 'next']
}
</script>

<style scoped>
.prompts-wrap { padding: 0 0 32rpx; }
.prompts-tabs { display: flex; gap: 16rpx; margin-bottom: 24rpx; padding: 0 4rpx; }
.prompts-tab { font-size: 24rpx; color: #666; padding: 14rpx 28rpx; border-radius: 32rpx; background: #fff; line-height: 1; box-shadow: 0 1rpx 4rpx rgba(0,0,0,.05); flex: 1; text-align: center; }
.prompts-tab-active { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; font-weight: 500; box-shadow: 0 4rpx 12rpx rgba(102,126,234,.3); }
.prompts-title { display: block; font-size: 26rpx; color: #999; margin-bottom: 20rpx; font-weight: 400; }
.prompt-item { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 28rpx; margin-bottom: 14rpx; background: #fff; border-radius: 16rpx; box-shadow: 0 1rpx 6rpx rgba(0,0,0,.04); }
.prompt-item:active { background: #f8f9ff; transform: scale(.98); }
.prompt-text { font-size: 26rpx; color: #333; flex: 1; padding-right: 16rpx; line-height: 1.4; }
.prompt-arrow { font-size: 22rpx; color: #bbb; flex-shrink: 0; }
.prompts-footer { display: flex; align-items: center; justify-content: center; gap: 24rpx; margin-top: 28rpx; }
.prompts-page { font-size: 22rpx; color: #bbb; }
.prompts-next { font-size: 24rpx; color: #667eea; padding: 10rpx 24rpx; border: 2rpx solid #667eea; border-radius: 30rpx; }
.prompts-next:active { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; border-color: transparent; }
</style>
