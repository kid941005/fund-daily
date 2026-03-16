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
    
    <!-- 热门板块 -->
    <section class="section sectors">
      <h2>🔥 热门板块</h2>
      <div class="sector-list">
        <div v-for="sector in sectors" :key="sector.name" class="sector-item">
          <span class="name">{{ sector.name }}</span>
          <span class="change" :class="sector.change >= 0 ? 'up' : 'down'">
            {{ sector.change >= 0 ? '↑' : '↓' }}{{ Math.abs(sector.change).toFixed(2) }}%
          </span>
        </div>
      </div>
    </section>
    
    <!-- 热点资讯 -->
    <section class="section news">
      <h2>📰 热点资讯</h2>
      <div v-if="newsLoading" class="loading">加载中...</div>
      <div v-else class="news-list">
        <div v-for="item in news" :key="item.url" class="news-item">
          <span class="title">{{ item.title }}</span>
          <span class="time">{{ item.time }}</span>
        </div>
      </div>
    </section>
    
    <!-- 基金列表 -->
    <section class="section funds">
      <h2>💰 我的持仓</h2>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else class="fund-list">
        <div v-for="fund in funds" :key="fund.code" class="fund-item">
          <div class="fund-info">
            <span class="code">{{ fund.code }}</span>
            <span class="name">{{ fund.name || '未知' }}</span>
          </div>
          <div class="fund-nav">
            <span class="nav">净值: {{ fund.nav || '--' }}</span>
            <span class="change" :class="fund.trend">{{ fund.daily_change }}%</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useFundStore } from '@/stores/fund'

const store = useFundStore()

const funds = computed(() => store.holdings)
const sectors = computed(() => store.sectors)
const advice = computed(() => store.advice)
const loading = computed(() => store.loading.funds)
const news = computed(() => store.news)
const newsLoading = computed(() => store.loading.news)

const sentimentClass = computed(() => {
  const sentiment = advice.value?.market_sentiment
  if (sentiment?.includes('乐观') || sentiment?.includes('上涨')) return 'up'
  if (sentiment?.includes('谨慎') || sentiment?.includes('下跌')) return 'down'
  return ''
})

onMounted(() => {
  if (store.funds.length === 0) {
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

.sector-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.sector-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f8f9fa;
  border-radius: 20px;
}

.sector-item .name {
  font-size: 14px;
}

.sector-item .change {
  font-size: 14px;
  font-weight: bold;
}

.sector-item .change.up { color: #ef4444; }
.sector-item .change.down { color: #22c55e; }

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

.fund-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.fund-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.fund-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.fund-info .code {
  font-size: 14px;
  color: #666;
}

.fund-info .name {
  font-size: 16px;
  font-weight: 500;
}

.fund-nav {
  text-align: right;
}

.fund-nav .nav {
  display: block;
  font-size: 12px;
  color: #999;
}

.fund-nav .change {
  font-size: 18px;
  font-weight: bold;
}

.fund-nav .change.up { color: #ef4444; }
.fund-nav .change.down { color: #22c55e; }

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
}
</style>
