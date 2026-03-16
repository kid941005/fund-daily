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
            <span class="value">{{ analysis?.risk_metrics?.risk_level || '--' }}</span>
          </div>
          <div class="risk-card">
            <span class="label">风险评分</span>
            <span class="value">{{ analysis?.risk_metrics?.risk_score || 0 }}</span>
          </div>
          <div class="risk-card">
            <span class="label">基金数量</span>
            <span class="value">{{ analysis?.risk_metrics?.fund_count || 0 }}</span>
          </div>
          <div class="risk-card">
            <span class="label">分散度</span>
            <span class="value">{{ analysis?.risk_metrics?.diversification || '--' }}</span>
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
        
        <!-- 详细表格 -->
        <div class="detail-table">
          <h3>📋 持仓明细</h3>
          <table>
            <thead>
              <tr>
                <th>基金</th>
                <th>持仓金额</th>
                <th>当前占比</th>
                <th>目标占比</th>
                <th>评分</th>
                <th>建议</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="fund in analysis?.funds" :key="fund.fund_code">
                <td>
                  <div class="fund-name">{{ fund.fund_name }}</div>
                  <div class="fund-code">{{ fund.fund_code }}</div>
                </td>
                <td>¥{{ (fund.amount || 0).toFixed(2) }}</td>
                <td>{{ fund.current_pct || 0 }}%</td>
                <td>{{ fund.target_pct || 0 }}%</td>
                <td>
                  <span class="score-badge" :class="getScoreClass(fund.score_100?.total_score)">
                    {{ fund.score_100?.total_score || '--' }}
                  </span>
                </td>
                <td>{{ getSuggestion(fund) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '@/api'

const pieChart = ref(null)
const barChart = ref(null)
const analysis = ref(null)
const loading = ref(true)

const fetchAnalysis = async () => {
  loading.value = true
  try {
    const data = await api.getAnalysis()
    console.log('API返回:', data)
    analysis.value = data.analysis || data
    console.log('分析数据:', analysis.value)
    nextTick(initCharts)
  } catch (e) {
    console.error('Failed to fetch analysis:', e)
  } finally {
    loading.value = false
  }
}

const initCharts = () => {
  console.log('initCharts called', analysis.value)
  if (!analysis.value?.funds) {
    console.log('No funds data')
    return
  }
  
  console.log('Funds count:', analysis.value.funds.length)
  console.log('pieChart ref:', pieChart.value)
  console.log('barChart ref:', barChart.value)
  
  // 饼图：持仓分布
  if (pieChart.value) {
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
  
  // 柱状图：评分分布
  if (barChart.value) {
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

onMounted(fetchAnalysis)
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

.score-badge.excellent { background: #dcfce7; color: #22c55e; }
.score-badge.good { background: #e0e7ff; color: #667eea; }
.score-badge.fair { background: #fef3c7; color: #f59e0b; }
.score-badge.poor { background: #fee2e2; color: #ef4444; }
</style>
