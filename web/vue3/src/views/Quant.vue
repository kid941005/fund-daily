<template>
  <div class="quant">
    <h1>📊 量化分析</h1>
    
    <!-- 择时信号 -->
    <section class="section">
      <h2>🎯 市场择时</h2>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else class="timing-grid">
        <div class="timing-card">
          <span class="label">市场趋势</span>
          <span class="value" :class="timingSignals.trend === '上涨' ? 'up' : 'down'">
            {{ timingSignals.trend || '--' }}
          </span>
        </div>
        <div class="timing-card">
          <span class="label">建议</span>
          <span class="value">{{ timingSignals.action || '--' }}</span>
        </div>
        <div class="timing-card">
          <span class="label">信心指数</span>
          <span class="value">{{ timingSignals.confidence || 0 }}%</span>
        </div>
        <div class="timing-card">
          <span class="label">风险等级</span>
          <span class="value" :class="getRiskClass(timingSignals.risk)">
            {{ timingSignals.risk || '--' }}
          </span>
        </div>
      </div>
    </section>
    
    <!-- 组合优化 -->
    <section class="section">
      <h2>📈 组合优化</h2>
      <div v-if="optimizeLoading" class="loading">加载中...</div>
      <div v-else-if="portfolioOptimize.recommendations" class="optimize-content">
        <div class="summary">
          <div class="summary-item">
            <span class="label">当前基金数</span>
            <span class="value">{{ portfolioOptimize.current_count || 0 }}</span>
          </div>
          <div class="summary-item">
            <span class="label">建议基金数</span>
            <span class="value">{{ portfolioOptimize.recommended_count || 0 }}</span>
          </div>
          <div class="summary-item">
            <span class="label">预期收益</span>
            <span class="value up">{{ portfolioOptimize.expected_return || 0 }}%</span>
          </div>
        </div>
        
        <div class="recommendations">
          <h3>优化建议</h3>
          <div v-for="rec in portfolioOptimize.recommendations" :key="rec.fund_code" 
               class="rec-item" :class="rec.action">
            <span class="fund-name">{{ rec.fund_name || rec.fund_code }}</span>
            <span class="action">{{ rec.action }}</span>
            <span class="reason">{{ rec.reason }}</span>
          </div>
        </div>
      </div>
      <div v-else class="empty">暂无优化建议</div>
    </section>
    
    <!-- 调仓建议 -->
    <section class="section">
      <h2>⚖️ 调仓建议</h2>
      <div v-if="rebalancingLoading" class="loading">加载中...</div>
      <div v-else-if="rebalancing.trades" class="rebalancing-content">
        <div class="summary">
          <div class="summary-item">
            <span class="label">需调整基金数</span>
            <span class="value">{{ rebalancing.trades?.length || 0 }}</span>
          </div>
          <div class="summary-item">
            <span class="label">总交易金额</span>
            <span class="value">¥{{ (rebalancing.total_amount || 0).toFixed(2) }}</span>
          </div>
        </div>
        
        <div class="trades">
          <h3>交易清单</h3>
          <table class="trade-table">
            <thead>
              <tr>
                <th>基金</th>
                <th>操作</th>
                <th>当前仓位</th>
                <th>目标仓位</th>
                <th>调整金额</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="trade in rebalancing.trades" :key="trade.fund_code">
                <td>{{ trade.fund_name || trade.fund_code }}</td>
                <td :class="trade.action">{{ trade.action }}</td>
                <td>{{ (trade.current_pct || 0).toFixed(1) }}%</td>
                <td>{{ (trade.target_pct || 0).toFixed(1) }}%</td>
                <td :class="trade.action">¥{{ Math.abs(trade.target_amount || 0).toFixed(2) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-else class="empty">暂无调仓建议</div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useFundStore } from '@/stores/fund'

const store = useFundStore()

const timingSignals = computed(() => store.timingSignals)
const portfolioOptimize = computed(() => store.portfolioOptimize)
const rebalancing = computed(() => store.rebalancing)

const loading = computed(() => store.loading.timing)
const optimizeLoading = computed(() => store.loading.optimize)
const rebalancingLoading = computed(() => store.loading.rebalancing)

const getRiskClass = (risk) => {
  if (!risk) return ''
  if (risk.includes('低')) return 'low'
  if (risk.includes('中')) return 'medium'
  if (risk.includes('高')) return 'high'
  return ''
}

onMounted(() => {
  store.fetchTimingSignals()
  store.fetchPortfolioOptimize()
  store.fetchRebalancing()
})
</script>

<style scoped>
.quant {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

h1 {
  font-size: 24px;
  margin-bottom: 8px;
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

.section h3 {
  margin: 16px 0 12px;
  font-size: 16px;
  color: #666;
}

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #999;
}

/* 择时卡片 */
.timing-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.timing-card {
  text-align: center;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.timing-card .label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.timing-card .value {
  font-size: 20px;
  font-weight: bold;
}

.timing-card .value.up { color: #ef4444; }
.timing-card .value.down { color: #22c55e; }
.timing-card .value.low { color: #22c55e; }
.timing-card .value.medium { color: #f59e0b; }
.timing-card .value.high { color: #ef4444; }

/* 摘要 */
.summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.summary-item {
  text-align: center;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.summary-item .label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.summary-item .value {
  font-size: 24px;
  font-weight: bold;
}

.summary-item .value.up { color: #ef4444; }
.summary-item .value.down { color: #22c55e; }

/* 建议 */
.recommendations, .trades {
  margin-top: 20px;
}

.rec-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px;
  margin-bottom: 8px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #ccc;
}

.rec-item.buy { border-left-color: #ef4444; }
.rec-item.sell { border-left-color: #22c55e; }
.rec-item.keep { border-left-color: #f59e0b; }

.rec-item .fund-name {
  flex: 1;
  font-weight: 500;
}

.rec-item .action {
  font-weight: bold;
}

.rec-item .action.buy { color: #ef4444; }
.rec-item .action.sell { color: #22c55e; }
.rec-item .action.keep { color: #f59e0b; }

.rec-item .reason {
  color: #666;
  font-size: 14px;
}

/* 交易表格 */
.trade-table {
  width: 100%;
  border-collapse: collapse;
}

.trade-table th,
.trade-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.trade-table th {
  background: #f8f9fa;
  font-weight: 600;
}

.trade-table td.buy { color: #ef4444; }
.trade-table td.sell { color: #22c55e; }

@media (max-width: 768px) {
  .timing-grid,
  .summary {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
