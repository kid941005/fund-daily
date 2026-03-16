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
    
    <!-- ECharts 图表 -->
    <section class="section charts">
      <div class="chart-container">
        <div ref="sectorChart" class="chart"></div>
      </div>
      <div class="chart-container">
        <div ref="scoreChart" class="chart"></div>
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
    
    <!-- 雪球热度 -->
    <section class="section xueqiu">
      <h2>🌡️ 雪球热度榜</h2>
      <div v-if="xueqiuLoading" class="loading">加载中...</div>
      <div v-else class="hot-list">
        <div v-for="(item, index) in xueqiuHot" :key="item.code" class="hot-item">
          <span class="rank">{{ index + 1 }}</span>
          <span class="name">{{ item.name || item.code }}</span>
          <span class="hot-value">🔥 {{ item.hot || 0 }}</span>
        </div>
      </div>
    </section>
    
    <!-- 基金列表 -->
    <section class="section funds">
      <h2>📈 基金行情</h2>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else class="fund-list">
        <div v-for="fund in funds" :key="fund.fund_code" class="fund-item">
          <div class="fund-info">
            <span class="code">{{ fund.fund_code }}</span>
            <span class="name">{{ fund.fund_name }}</span>
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
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useFundStore } from '@/stores/fund'

const store = useFundStore()
const sectorChart = ref(null)
const scoreChart = ref(null)

const funds = computed(() => store.funds)
const sectors = computed(() => store.sectors)
const xueqiuHot = ref([])
const xueqiuLoading = ref(false)
const advice = computed(() => store.advice)
const loading = computed(() => store.loading.funds)

const sentimentClass = computed(() => {
  const sentiment = advice.value?.market_sentiment
  if (sentiment?.includes('乐观') || sentiment?.includes('上涨')) return 'up'
  if (sentiment?.includes('谨慎') || sentiment?.includes('下跌')) return 'down'
  return ''
})

const initCharts = () => {
  // 板块图表
  if (sectorChart.value && sectors.value.length > 0) {
    const chart = echarts.init(sectorChart.value)
    const data = sectors.value.slice(0, 10).map(s => ({
      name: s.name,
      value: Math.abs(s.change)
    }))
    chart.setOption({
      title: { text: '板块涨跌幅', left: 'center' },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: data.map(d => d.name) },
      yAxis: { type: 'value' },
      series: [{
        type: 'bar',
        data: data.map((d, i) => ({
          value: d.value,
          itemStyle: { color: sectors.value[i]?.change >= 0 ? '#ef4444' : '#22c55e' }
        }))
      }]
    })
  }
  
  // 评分图表
  if (scoreChart.value && advice.value?.funds) {
    const chart = echarts.init(scoreChart.value)
    const fundScores = advice.value.funds.slice(0, 5).map(f => ({
      name: f.fund_name?.substring(0, 6) || f.fund_code,
      value: f.score_100?.total_score || 0
    }))
    chart.setOption({
      title: { text: '基金评分', left: 'center' },
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: '50%',
        data: fundScores,
        label: { formatter: '{b}: {c}分' }
      }]
    })
  }
}

// 获取雪球热度
const fetchXueqiuHot = async () => {
  xueqiuLoading.value = true
  try {
    const res = await fetch('/api/external/hot-rank?limit=10')
    const data = await res.json()
    if (data.success) {
      xueqiuHot.value = data.data || []
    }
  } catch (e) {
    console.error('Failed to fetch xueqiu hot:', e)
  } finally {
    xueqiuLoading.value = false
  }
}

watch([sectors, () => advice.value?.funds], () => {
  nextTick(initCharts)
}, { deep: true })

onMounted(() => {
  if (store.funds.length === 0) {
    store.loadAll()
  }
  setTimeout(initCharts, 1000)
  
  // 获取雪球热度
  fetchXueqiuHot()
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

.charts {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.chart-container {
  height: 300px;
}

.chart {
  width: 100%;
  height: 100%;
}

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

.xueqiu {
  background: linear-gradient(135deg, #ff6b6b 0%, #ffa500 100%);
  color: white;
}

.xueqiu .loading {
  color: white;
}

.hot-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hot-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: rgba(255,255,255,0.9);
  border-radius: 6px;
}

.hot-item .rank {
  font-weight: bold;
  color: #ff6b6b;
  width: 24px;
}

.hot-item .name {
  flex: 1;
}

.hot-item .hot-value {
  color: #ffa500;
  font-weight: bold;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
}
</style>
