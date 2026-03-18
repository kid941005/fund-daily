<template>
  <div class="quant">
    <h1>📊 量化分析</h1>
    
    <!-- 市场择时 -->
    <section class="section">
      <h2>🎯 市场择时</h2>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else class="timing-cards">
        <!-- 综合信号 & 信心指数 -->
        <div class="timing-main">
          <span class="label">综合信号</span>
          <span class="value" :class="getSignalClass(timingSignals.overall_signal)">
            {{ timingSignals.overall_signal || '--' }}
          </span>
        </div>
        <div class="timing-main">
          <span class="label">信心指数</span>
          <span class="value">{{ timingSignals.score || 0 }}</span>
        </div>
        
        <!-- 细分信号 -->
        <div v-for="(sig, idx) in timingSignals.signals" :key="idx" class="timing-main">
          <span class="label">{{ sig.type }}</span>
          <span class="value" :class="getSignalClass(sig.signal)">{{ sig.signal }}</span>
          <span class="reason">{{ sig.reason }}</span>
        </div>
      </div>
    </section>
    
    <!-- 动态权重 -->
    <section class="section" v-if="dynamicWeights">
      <h2>⚙️ 动态权重 (当前: {{ dynamicWeights.market_cycle }})</h2>
      <div class="weights-grid">
        <div v-for="(label, key) in weightLabels" :key="key" class="weight-item">
          <span class="weight-label">{{ label }}</span>
          <span class="weight-value">{{ dynamicWeights.weights[key] }}分</span>
        </div>
      </div>
    </section>
    
    <!-- 量化评分 -->
    <section class="section">
      <h2>📊 量化评分</h2>
      
      <!-- 排序控制 -->
      <div class="sort-controls" v-if="store.funds?.length">
        <button class="sort-btn" @click="toggleSortOrder">
          {{ sortOrder === 'desc' ? '🔽 分数排序（高分优先）' : '🔼 分数排序（低分优先）' }}
        </button>
      </div>
      
      <div v-if="store.funds?.length" class="score-cards">
        <div v-for="fund in sortedFunds" :key="fund.fund_code" class="score-card">
          <div class="score-header">
            <span class="name">{{ fund.fund_name?.substring(0, 10) }}</span>
            <span class="score" :class="getScoreClass(fund.score_100?.total_score)">
              {{ fund.score_100?.total_score || '--' }}分
            </span>
          </div>
          <div class="score-details">
            <div class="detail">
              <span>估值</span>
              <span>{{ fund.score_100?.details?.details?.valuation?.score || 0 }}/25</span>
            </div>
            <div class="detail">
              <span>业绩</span>
              <span>{{ fund.score_100?.details?.details?.performance?.score || 0 }}/20</span>
            </div>
            <div class="detail">
              <span>风险</span>
              <span>{{ fund.score_100?.details?.details?.risk_control?.score || 0 }}/15</span>
            </div>
            <div class="detail">
              <span>动量</span>
              <span>{{ fund.score_100?.details?.details?.momentum?.score || 0 }}/15</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty">暂无评分数据</div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useFundStore } from '@/stores/fund'
import axios from 'axios'

const store = useFundStore()
const timingSignals = computed(() => store.timingSignals)
const portfolioOptimize = computed(() => store.portfolioOptimize)
const rebalancing = computed(() => store.rebalancing)
const loading = computed(() => store.loading.timing)
const optimizeLoading = computed(() => store.loading.optimize)
const rebalancingLoading = computed(() => store.loading.rebalancing)

// 排序相关
const sortOrder = ref('desc') // desc: 高分优先, asc: 低分优先

// 排序后的基金列表
const sortedFunds = computed(() => {
  if (!store.funds?.length) return []
  
  const funds = [...store.funds]
  
  return funds.sort((a, b) => {
    const scoreA = a.score_100?.total_score || 0
    const scoreB = b.score_100?.total_score || 0
    
    if (sortOrder.value === 'desc') {
      return scoreB - scoreA // 高分优先
    } else {
      return scoreA - scoreB // 低分优先
    }
  })
})

// 动态权重数据
const dynamicWeights = ref(null)
const weightsLoading = ref(false)

store.fetchTimingSignals()
store.fetchPortfolioOptimize()
store.fetchRebalancing()

const getScoreClass = (score) => {
  if (!score) return ''
  if (score >= 70) return 'excellent'
  if (score >= 50) return 'good'
  if (score >= 30) return 'fair'
  return 'poor'
}

// 排序函数
const toggleSortOrder = () => {
  sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
}

// 获取动态权重
async function fetchDynamicWeights() {
  weightsLoading.value = true
  try {
    const res = await axios.get('/api/quant/dynamic-weights')
    if (res.data.success) {
      dynamicWeights.value = res.data.data
    }
  } catch (e) {
    console.error('Failed to fetch dynamic weights:', e)
  } finally {
    weightsLoading.value = false
  }
}

onMounted(() => {
  fetchDynamicWeights()
})

function getSignalClass(signal) {
  if (signal === '买入') return 'buy'
  if (signal === '卖出') return 'sell'
  if (signal === '持有') return 'keep'
  return ''
}

// 权重项名称映射
const weightLabels = {
  valuation: '估值面',
  performance: '业绩表现',
  risk_control: '风险控制',
  momentum: '动量趋势',
  sentiment: '市场情绪',
  sector: '板块景气',
  manager: '基金经理',
  liquidity: '流动性'
}

// 计算最高权重
const maxWeight = computed(() => {
  if (!portfolioOptimize.value?.allocations?.length) return 0
  const weights = portfolioOptimize.value.allocations.map(a => a.weight || 0)
  return Math.max(...weights).toFixed(1)
})
</script>

<style scoped>
.quant {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 16px;
}

h1 {
  font-size: 24px;
  margin-bottom: 8px;
}

h2 {
  font-size: 18px;
  color: #333;
  margin: 0 0 16px;
}

h3 {
  font-size: 14px;
  color: #666;
  margin: 16px 0 12px;
}

.section {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.timing-cards {
  display: flex;
  gap: 8px;
  flex-wrap: nowrap;
  overflow-x: auto;
  padding-bottom: 8px;
}

.timing-main {
  flex: 1;
  min-width: 0;
  text-align: center;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  flex-shrink: 0;
}

.timing-main .label {
  display: block;
  font-size: 11px;
  color: #666;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.timing-main .value {
  font-size: 18px;
  font-weight: bold;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.timing-main .reason {
  display: block;
  font-size: 10px;
  color: #999;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.timing-main .value.buy { color: #ef4444; }
.timing-main .value.sell { color: #22c55e; }
.timing-main .value.keep { color: #f59e0b; }

.weights-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.weight-item {
  text-align: center;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 6px;
}

.weight-label {
  display: block;
  font-size: 11px;
  color: #666;
}

.weight-value {
  display: block;
  font-size: 14px;
  font-weight: bold;
  color: #333;
}

.optimize-summary, .rebalance-summary {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.opt-stat, .rb-stat {
  flex: 1;
  text-align: center;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.opt-stat .label, .rb-stat .label {
  display: block;
  font-size: 11px;
  color: #666;
  margin-bottom: 4px;
}

.opt-stat .value, .rb-stat .value {
  font-size: 20px;
  font-weight: bold;
}

.rb-stat .value.keep { color: #f59e0b; }
.rb-stat .value.sell { color: #22c55e; }
.rb-stat .value.buy { color: #ef4444; }

.allocation-list, .trade-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.allocation-item, .trade-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 12px;
}

.fund-info, .trade-info {
  flex: 1;
  min-width: 0;
}

.fund-code, .trade-info .fund-code {
  font-weight: bold;
  color: #333;
}

.fund-name {
  display: block;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fund-stats {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* 排序控制 */
.sort-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.sort-btn {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.sort-btn:hover {
  background: #f5f5f5;
}

.sort-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.score-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.score-card {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.score-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.score-header .name {
  font-weight: 500;
}

.score-header .score {
  font-size: 20px;
  font-weight: bold;
}

.score.excellent { color: #22c55e; }
.score.good { color: #667eea; }
.score.fair { color: #f59e0b; }
.score.poor { color: #ef4444; }

.score-details {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.score-details .detail {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
}

.score-details .detail span:first-child {
  color: #333;
}

.score-details .detail span:last-child {
  font-weight: 500;
}

.trade-action {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 11px;
}

.trade-action.持有 { background: #fef3c7; color: #d97706; }
.trade-action.卖出 { background: #dcfce7; color: #16a34a; }
.trade-action.买入 { background: #fee2e2; color: #dc2626; }

.trade-detail { color: #666; }
.trade-reason { color: #999; font-size: 11px; }

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #999;
}

@media (max-width: 480px) {
  .quant { padding: 8px; }
  .section { padding: 12px; }
  .timing-cards {
    flex-direction: row;
    gap: 6px;
  }
  .timing-main {
    padding: 8px;
    min-width: 80px;
  }
  .timing-main .value {
    font-size: 16px;
  }
  .timing-main .reason {
    font-size: 9px;
  }
}
</style>
