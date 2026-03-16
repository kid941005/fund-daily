<template>
  <div class="home">
    <!-- 市场概览 -->
    <section class="section market-overview">
      <h2>📊 市场概览</h2>
      <div class="overview-cards">
        <div class="card">
          <span class="label">市场情绪</span>
          <span class="value" :class="sentimentClass">{{ advice?.market_sentiment || '--' }}</span>
        </div>
        <div class="card">
          <span class="label">市场评分</span>
          <span class="value">{{ advice?.market_score || 0 }}</span>
        </div>
        <div class="card">
          <span class="label">大宗商品</span>
          <span class="value">{{ advice?.commodity_sentiment || '--' }}</span>
        </div>
        <div class="card">
          <span class="label">建议操作</span>
          <span class="value action">{{ advice?.action || '--' }}</span>
        </div>
      </div>
    </section>
    
    <!-- 热门板块 - 柱状图 -->
    <section class="section sectors">
      <h2>🔥 热门板块</h2>
      <div class="sector-chart">
        <div v-for="sector in sectors.slice(0, 10)" :key="sector.name" class="sector-bar">
          <span class="name">{{ sector.name }}</span>
          <div class="bar-container">
            <div class="bar" :class="sector.change >= 0 ? 'up' : 'down'" 
                 :style="{ width: Math.min(Math.abs(sector.change) * 5, 100) + '%' }"></div>
          </div>
          <span class="change" :class="sector.change >= 0 ? 'up' : 'down'">
            {{ sector.change >= 0 ? '+' : '' }}{{ sector.change?.toFixed(2) }}%
          </span>
        </div>
      </div>
    </section>
    
    <!-- 热点资讯 -->
    <section class="section news">
      <h2>📰 热点资讯</h2>
      <div v-if="newsLoading" class="loading">加载中...</div>
      <div v-else class="news-list">
        <div v-for="item in news" :key="item.url" class="news-item" @click="openUrl(item.url)">
          <span class="title">{{ item.title }}</span>
          <span class="time">{{ item.time }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useFundStore } from '@/stores/fund'

const store = useFundStore()

const advice = computed(() => store.advice)
const sectors = computed(() => store.sectors)
const news = computed(() => store.news)
const newsLoading = computed(() => store.loading.news)

const sentimentClass = computed(() => {
  const sentiment = advice.value?.market_sentiment
  if (sentiment?.includes('乐观') || sentiment?.includes('上涨')) return 'up'
  if (sentiment?.includes('谨慎') || sentiment?.includes('下跌')) return 'down'
  return ''
})

const openUrl = (url) => {
  if (url) window.open(url, '_blank')
}

onMounted(() => {
  // 首页加载市场数据（如果缓存过期则刷新）
  if (store.sectors.length === 0) {
    store.loadAll()
  }
})
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.section h2 {
  margin: 0 0 16px;
  font-size: 18px;
  color: #333;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.card {
  text-align: center;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.card .label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.card .value {
  font-size: 20px;
  font-weight: bold;
}

.card .value.up { color: #ef4444; }
.card .value.down { color: #22c55e; }
.card .value.action { color: #667eea; }

.sector-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sector-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sector-bar .name {
  width: 100px;
  font-size: 14px;
  color: #333;
  text-align: right;
}

.bar-container {
  flex: 1;
  height: 20px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.bar.up { background: linear-gradient(90deg, #ff6b6b, #ff8e8e); }
.bar.down { background: linear-gradient(90deg, #22c55e, #4ade80); }

.sector-bar .change {
  width: 70px;
  text-align: right;
  font-weight: bold;
  font-size: 14px;
}

.sector-bar .change.up { color: #ef4444; }
.sector-bar .change.down { color: #22c55e; }

.news-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.news-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.news-item:hover {
  background: #e9ecef;
}

.news-item .title {
  flex: 1;
  font-size: 14px;
  color: #333;
}

.news-item .time {
  font-size: 12px;
  color: #999;
  margin-left: 12px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
}

@media (max-width: 768px) {
  .overview-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
