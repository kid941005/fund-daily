<template>
  <div class="quant">
    <h1>📊 量化分析</h1>
    
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
    
    <!-- 市场择时 -->
    <section class="section">
      <h2>🎯 市场择时</h2>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else>
        <div class="timing-summary">
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
        </div>
        
        <div class="timing-signals" v-if="timingSignals.signals?.length">
          <h3>细分信号</h3>
          <div class="signal-list">
            <div v-for="(sig, idx) in timingSignals.signals" :key="idx" class="signal-item">
              <div class="signal-type">{{ sig.type }}</div>
              <div class="signal-value" :class="getSignalClass(sig.signal)">{{ sig.signal }}</div>
              <div class="signal-reason">{{ sig.reason }}</div>
              <div class="signal-weight">权重: {{ (sig.weight * 100).toFixed(0) }}%</div>
            </div>
          </div>
        </div>
      </div>
    </section>
    
    <!-- 组合优化 -->
    <section class="section">
      <h2>📈 组合优化</h2>
      <div v-if="optimizeLoading" class="loading">加载中...</div>
      <div v-else-if="portfolioOptimize.allocations?.length">
        <div class="optimize-summary">
          <div class="opt-stat">
            <span class="label">基金数量</span>
            <span class="value">{{ portfolioOptimize.allocations.length }}</span>
          </div>
          <div class="opt-stat">
            <span class="label">策略</span>
            <span class="value">评分加权</span>
          </div>
          <div class="opt-stat">
            <span class="label">最高权重</span>
            <span class="value">{{ maxWeight }}%</span>
          </div>
        </div>
        
        <h3>持仓建议</h3>
        <div class="allocation-list">
          <div v-for="item in portfolioOptimize.allocations" :key="item.fund_code" 
               class="allocation-item">
            <div class="fund-info">
              <span class="fund-code">{{ item.fund_code }}</span>
              <span class="fund-name">{{ item.fund_name }}</span>
            </div>
            <div class="fund-stats">
              <span class="score" :class="getScoreClass(item.score)">{{ item.score }}分</span>
              <span class="weight">{{ item.weight?.toFixed(1) }}%</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty">暂无优化建议</div>
    </section>
    
    <!-- 调仓建议 -->
    <section class="section">
      <h2>⚖️ 调仓建议</h2>
      <div v-if="rebalancingLoading" class="loading">加载中...</div>
      <div v-else-if="rebalancing.trades?.length">
        <div class="rebalance-summary">
          <div class="rb-stat">
            <span class="label">持有</span>
            <span class="value keep">{{ rebalancing.summary?.hold_count || 0 }}</span>
          </div>
          <div class="rb-stat">
            <span class="label">卖出</span>
            <span class="value sell">{{ rebalancing.summary?.sell_count || 0 }}</span>
          </div>
          <div class="rb-stat">
            <span class="label">买入</span>
            <span class="value buy">{{ rebalancing.summary?.buy_count || 0 }}</span>
          </div>
        </div>
        
        <h3>调整明细</h3>
        <div class="trade-list">
          <div v-for="trade in rebalancing.trades" :key="trade.fund_code" 
               class="trade-item" :class="trade.action">
            <div class="trade-info">
              <span class="fund-code">{{ trade.fund_code }}</span>
              <span class="fund-name">{{ trade.fund_name }}</span>
            </div>
            <div class="trade-action" :class="trade.action">{{ trade.action }}</div>
            <div class="trade-detail">
              当前 {{ trade.current_pct?.toFixed(1) }}% → 目标 {{ trade.target_pct?.toFixed(1) }}%
            </div>
            <div class="trade-reason">{{ trade.reason }}</div>
          </div>
        </div>
      </div>
      <div v-else class="empty">暂无调仓建议</div>
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

// 动态权重数据
const dynamicWeights = ref(null)
const weightsLoading = ref(false)

store.fetchTimingSignals()
store.fetchPortfolioOptimize()
store.fetchRebalancing()

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

function getScoreClass(score) {
  if (score >= 70) return 'high'
  if (score >= 50) return 'medium'
  return 'low'
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

.timing-summary {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.timing-main {
  flex: 1;
  text-align: center;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.timing-main .label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.timing-main .value {
  font-size: 24px;
  font-weight: bold;
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

.signal-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.signal-item {
  display: grid;
  grid-template-columns: 80px 60px 1fr 50px;
  align-items: center;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 12px;
}

.signal-type { font-weight: bold; color: #333; }
.signal-value { font-weight: bold; }
.signal-value.buy { color: #ef4444; }
.signal-value.sell { color: #22c55e; }
.signal-value.keep { color: #f59e0b; }
.signal-reason { color: #666; }
.signal-weight { color: #999; text-align: right; }

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

.score {
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: bold;
}

.score.high { background: #dcfce7; color: #16a34a; }
.score.medium { background: #fef3c7; color: #d97706; }
.score.low { background: #fee2e2; color: #dc2626; }

.weight { color: #666; }

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
  .timing-summary { flex-direction: column; }
  .signal-item { grid-template-columns: 1fr 60px; }
  .signal-reason, .signal-weight { display: none; }
}
</style>
