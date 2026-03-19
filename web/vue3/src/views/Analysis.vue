<template>
  <div class="analysis">
    <section class="section">
      <h2>📊 持仓分析</h2>
      
      <div v-if="loading" class="loading">加载中...</div>
      
      <template v-else>
        <!-- 风险指标 -->
        <div class="risk-overview">
          <div class="risk-card">
            <span class="label">风险等级</span>
            <span class="value">{{ analysis?.risk_level || '--' }}</span>
          </div>
          <div class="risk-card">
            <span class="label">风险评分</span>
            <span class="value">{{ analysis?.risk_score || 0 }}</span>
          </div>
          <div class="risk-card">
            <span class="label">基金数量</span>
            <span class="value">{{ analysis?.fund_count || 0 }}</span>
          </div>
          <div class="risk-card">
            <span class="label">分散度</span>
            <span class="value">{{ analysis?.diversification || '--' }}</span>
          </div>
        </div>
        
        <!-- ECharts 可视化 -->
        <div class="charts-grid">
          <div class="chart-box">
            <h3>持仓分布</h3>
            <div ref="pieChart" class="chart"></div>
          </div>
          <div class="chart-box">
            <h3>评分分布</h3>
            <div ref="barChart" class="chart"></div>
          </div>
        </div>
        
        <!-- 建议 -->
        <div v-if="analysis?.allocation" class="suggestions">
          <h3>💡 投资建议</h3>
          <ul>
            <li v-for="(suggestion, index) in analysis.allocation.suggestions" :key="index">
              {{ suggestion }}
            </li>
          </ul>
        </div>
        
        </template>
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
        
        <!-- 转换建议 -->
        <div v-if="rebalancing.summary?.conversion_advice?.length" class="conversion-advice">
          <h3>🔄 转换建议</h3>
          <div class="advice-content">
            <p v-for="(advice, index) in rebalancing.summary.conversion_advice" :key="index">
              {{ advice }}
            </p>
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
import { ref, computed, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import { TooltipComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

// 注册必需的组件（tree-shaking）
echarts.use([
  PieChart,
  BarChart,
  TooltipComponent,
  GridComponent,
  CanvasRenderer,
])

import api from '@/api'
import { useFundStore } from '@/stores/fund'

const pieChart = ref(null)
const barChart = ref(null)
const store = useFundStore()
const analysis = ref(null)
const rebalancing = computed(() => store.rebalancing)
const rebalancingLoading = computed(() => store.loading.rebalancing)

const sortByScore = (order) => {
  sortOrder.value = order
}
const loading = ref(true)

store.fetchRebalancing()

const fetchAnalysis = async () => {
  loading.value = true
  try {
    const data = await api.getAnalysis()
    analysis.value = data.analysis || data
    nextTick(initCharts)
  } catch (e) {
    console.error('Failed to fetch analysis:', e)
  } finally {
    loading.value = false
  }
}

const initCharts = () => {
  if (!analysis.value?.funds) {
    return
  }
  
  
  // 延迟一下确保 DOM 渲染完成
  setTimeout(() => {
    initPieChart()
    initBarChart()
  }, 100)
}

const initPieChart = () => {
  if (!pieChart.value) return
  
  const chart = echarts.init(pieChart.value)
  const data = analysis.value.funds
    .filter(f => f.amount > 0)
    .map(f => ({
      name: f.fund_name?.substring(0, 8) || f.fund_code,
      value: f.amount || 0
    }))
  
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data,
      label: { show: false },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  })
}

const initBarChart = () => {
  if (!barChart.value) return
  
  const chart = echarts.init(barChart.value)
  const data = analysis.value.funds.map(f => ({
    name: f.fund_name?.substring(0, 6) || f.fund_code,
    value: f.score_100?.total_score || 0
  }))
  
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: data.map(d => d.name) },
    yAxis: { type: 'value', max: 100 },
    series: [{
      type: 'bar',
      data: data.map(d => ({
        value: d.value,
        itemStyle: {
          color: d.value >= 70 ? '#22c55e' : d.value >= 50 ? '#667eea' : d.value >= 30 ? '#f59e0b' : '#ef4444'
        }
      }))
    }]
  })
}

const getScoreClass = (score) => {
  if (!score) return ''
  if (score >= 70) return 'excellent'
  if (score >= 50) return 'good'
  if (score >= 30) return 'fair'
  return 'poor'
}

const getSuggestion = (fund) => {
  const score = fund.score_100?.total_score || 0
  const current = fund.current_pct || 0
  const target = fund.target_pct || 0
  
  if (score < 20) return '清仓'
  if (score < 35) return '减仓'
  if (target > current) return '增持'
  if (target < current) return '减仓'
  return '持有'
}

onMounted(async () => {
  // 确保已登录
  await store.checkLogin()
  fetchAnalysis()
})
</script>

<style scoped>
.analysis {
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
  margin: 0 0 20px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
}

.risk-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.risk-card {
  text-align: center;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.risk-card .label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.risk-card .value {
  font-size: 20px;
  font-weight: bold;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.chart-box {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.chart-box h3 {
  margin: 0 0 16px;
  font-size: 14px;
  color: #666;
}

.chart {
  width: 100%;
  height: 280px;
}

.suggestions {
  padding: 16px;
  background: #f0f9ff;
  border-radius: 8px;
  margin-bottom: 24px;
}

.suggestions h3 {
  margin: 0 0 12px;
  font-size: 16px;
}

.suggestions ul {
  margin: 0;
  padding-left: 20px;
}

.suggestions li {
  margin-bottom: 8px;
  line-height: 1.6;
}

.detail-table {
  overflow-x: auto;
}

.detail-table h3 {
  margin: 0 0 16px;
}

.table-controls {
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
}

.btn-sort {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}

.btn-sort:hover {
  background: #f5f5f5;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  font-weight: 600;
  color: #666;
  font-size: 12px;
}

.fund-name {
  font-weight: 500;
}

.fund-code {
  font-size: 12px;
  color: #999;
}

.score-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: bold;
}


</style>

<style>
/* 移动端适配 */
@media (max-width: 768px) {
  .analysis {
    padding: 12px;
    gap: 16px;
  }
  
  .section {
    padding: 20px;
    border-radius: 14px;
  }
  
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .score-cards {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .score-card {
    padding: 16px;
  }
  
  .score-details {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .chart-container {
    height: 300px;
  }
  
  .fund-list {
    grid-template-columns: 1fr;
  }
  
  .fund-item {
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .analysis {
    padding: 8px;
  }
  
  .section {
    padding: 16px;
    border-radius: 12px;
  }
  
  .section-header h2 {
    font-size: 18px;
  }
  
  .score-card {
    padding: 12px;
  }
  
  .score-value {
    font-size: 28px;
  }
  
  .chart-container {
    height: 250px;
  }
  
  .fund-item {
    padding: 12px;
  }
  
  .fund-rank {
    font-size: 18px;
    width: 36px;
    height: 36px;
  }
}

/* 转换建议样式 */
.conversion-advice {
  padding: 16px;
  background: #f0f9ff;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #3b82f6;
}

.conversion-advice h3 {
  margin: 0 0 12px;
  font-size: 16px;
  color: #1e40af;
  display: flex;
  align-items: center;
  gap: 8px;
}

.conversion-advice h3::before {
  content: "🔄";
}

.advice-content {
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
}

.advice-content p {
  margin: 8px 0;
  padding-left: 12px;
}

.advice-content p:first-child {
  font-weight: 600;
  color: #1e40af;
}

/* 调仓建议样式 */
.rebalance-summary {
  display: flex;
  justify-content: center;
  gap: 32px;
  margin-bottom: 24px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.rb-stat {
  text-align: center;
}

.rb-stat .label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.rb-stat .value {
  font-size: 24px;
  font-weight: bold;
}

.rb-stat .value.keep { color: #667eea; }
.rb-stat .value.sell { color: #ef4444; }
.rb-stat .value.buy { color: #22c55e; }

.trade-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.trade-item {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #ddd;
}

.trade-item.keep { border-left-color: #667eea; }
.trade-item.sell { border-left-color: #ef4444; }
.trade-item.buy { border-left-color: #22c55e; }

.trade-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.trade-action {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.trade-action.keep { background: #e0e7ff; color: #667eea; }
.trade-action.sell { background: #fee2e2; color: #ef4444; }
.trade-action.buy { background: #dcfce7; color: #22c55e; }

.trade-detail {
  font-size: 14px;
  color: #666;
  margin-top: 4px;
}

.trade-reason {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.empty {
  text-align: center;
  padding: 40px;
  color: #999;
}
</style>
