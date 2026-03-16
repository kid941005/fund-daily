<template>
  <div class="holdings">
    <!-- 操作按钮 -->
    <section class="section actions">
      <div class="action-buttons">
        <button class="btn btn-primary" @click="showAdd = true">
          <span class="icon">➕</span> 添加持仓
        </button>
        <button class="btn btn-success" @click="triggerOCR">
          <span class="icon">📷</span> 截图导入
        </button>
        <button class="btn btn-secondary" @click="handleExport">
          <span class="icon">📤</span> 导出
        </button>
        <button class="btn btn-danger" @click="handleClear">
          <span class="icon">🗑️</span> 清仓
        </button>
      </div>
    </section>

    <!-- 总览统计 -->
    <section class="section summary-section">
      <div class="summary-grid">
        <div class="summary-card">
          <span class="label">基金数量</span>
          <span class="value">{{ store.holdings.length }}</span>
        </div>
        <div class="summary-card">
          <span class="label">总持仓</span>
          <span class="value">¥{{ totalAmount.toFixed(2) }}</span>
        </div>
        <div class="summary-card">
          <span class="label">平均涨跌</span>
          <span class="value" :class="avgChange >= 0 ? 'up' : 'down'">
            {{ avgChange >= 0 ? '+' : '' }}{{ avgChange.toFixed(2) }}%
          </span>
        </div>
        <div class="summary-card highlight">
          <span class="label">当日收益</span>
          <span class="value" :class="dailyProfit >= 0 ? 'up' : 'down'">
            {{ dailyProfit >= 0 ? '+' : '' }}¥{{ dailyProfit.toFixed(2) }}
          </span>
        </div>
      </div>
    </section>

    <!-- 排序切换 -->
    <section class="section sort-section">
      <div class="sort-header">
        <div class="sort-tabs">
          <button 
            v-for="tab in sortTabs" 
            :key="tab.key"
            class="tab"
            :class="{ active: sortBy === tab.key }"
            @click="sortBy = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
        <button class="sort-order" @click="sortOrder = sortOrder === 'desc' ? 'asc' : 'desc'">
          {{ sortOrder === 'desc' ? '↓ 降序' : '↑ 升序' }}
        </button>
      </div>
    </section>

    <!-- 持仓列表 -->
    <section class="section holdings-section">
      <div v-if="sortedHoldings.length === 0" class="empty">
        <p>暂无持仓</p>
        <div class="empty-actions">
          <button class="btn btn-primary" @click="showAdd = true">手动添加</button>
          <button class="btn btn-secondary" @click="triggerOCR">截图导入</button>
        </div>
      </div>
      
      <div v-else class="holding-list">
        <div v-for="holding in sortedHoldings" :key="holding.code" class="holding-card">
          <div class="card-header">
            <div class="fund-info">
              <span class="fund-name">{{ holding.name || '未知' }}</span>
              <span class="fund-code">{{ holding.code }}</span>
            </div>
            <button class="btn-delete" @click="removeHolding(holding.code)">✕</button>
          </div>
          
          <div class="card-stats">
            <div class="stat">
              <span class="label">持仓金额</span>
              <span class="value">¥{{ (holding.amount || 0).toFixed(2) }}</span>
            </div>
            <div class="stat">
              <span class="label">持仓收益</span>
              <span class="value" :class="getProfit(holding) >= 0 ? 'up' : 'down'">
                {{ getProfit(holding) >= 0 ? '+' : '' }}¥{{ getProfit(holding).toFixed(2) }}
              </span>
            </div>
            <div class="stat">
              <span class="label">今日涨跌</span>
              <span class="value" :class="getChange(holding) >= 0 ? 'up' : 'down'">
                {{ getChange(holding) >= 0 ? '+' : '' }}{{ getChange(holding).toFixed(2) }}%
              </span>
            </div>
            <div class="stat">
              <span class="label">当日收益</span>
              <span class="value" :class="getDailyProfit(holding) >= 0 ? 'up' : 'down'">
                {{ getDailyProfit(holding) >= 0 ? '+' : '' }}¥{{ getDailyProfit(holding).toFixed(2) }}
              </span>
            </div>
          </div>
          
          <div class="card-meta">
            <span>净值: {{ getNav(holding) }}</span>
            <span>估算: {{ getEstNav(holding) }}</span>
            <span>持有: {{ getHoldDays(holding) }}天</span>
          </div>
          
          <div class="card-edit">
            <input 
              v-model.number="holding.amount" 
              type="number" 
              @change="updateHolding(holding)"
              placeholder="输入金额"
            />
            <span class="unit">元</span>
            <button class="btn-save" @click="updateHolding(holding)">保存</button>
          </div>
        </div>
      </div>
    </section>

    <!-- OCR 导入弹窗 -->
    <div v-if="showOCR" class="modal" @click.self="showOCR = false">
      <div class="modal-content">
        <h2>📷 截图导入</h2>
        <div class="ocr-area">
          <input type="file" accept="image/*" @change="handleOCRFile" />
          <p>选择基金截图自动识别</p>
        </div>
        <button class="btn btn-secondary" @click="showOCR = false">关闭</button>
      </div>
    </div>

    <!-- 添加持仓弹窗 -->
    <div v-if="showAdd" class="modal" @click.self="showAdd = false">
      <div class="modal-content">
        <h2>添加持仓</h2>
        <div class="form-group">
          <label>基金代码</label>
          <input v-model="newHolding.code" placeholder="例如: 000001" maxlength="6" />
        </div>
        <div class="form-group">
          <label>持仓金额（元）</label>
          <input v-model.number="newHolding.amount" type="number" placeholder="例如: 10000" />
        </div>
        <div class="modal-actions">
          <button @click="showAdd = false">取消</button>
          <button class="primary" @click="addHolding">添加</button>
        </div>
      </div>
    </div>
  </div>
</template>


<script setup>
import { ref, computed, onMounted } from 'vue'
import { useFundStore } from '@/stores/fund'

const store = useFundStore()

// 页面加载时获取基金数据
onMounted(() => {
  if (store.funds.length === 0) {
    store.fetchFunds()
  }
})

// 弹窗状态
const showAdd = ref(false)
const showOCR = ref(false)
const newHolding = ref({ code: '', amount: '' })

// 排序
const sortBy = ref('amount')
const sortOrder = ref('desc')
const sortTabs = [
  { key: 'amount', label: '持仓金额' },
  { key: 'change', label: '今日涨跌' },
  { key: 'daily', label: '当日收益' }
]

// 计算属性
const totalAmount = computed(() => store.totalAmount)
const dailyProfit = computed(() => {
  // 简化计算：假设当日收益
  return store.holdings.reduce((sum, h) => {
    return sum + (h.amount || 0) * 0.01
  }, 0) * -1
})
const avgChange = computed(() => {
  // 简化：随机值或从API获取
  return -1.5
})

const sortedHoldings = computed(() => {
  const list = [...store.holdings]
  const order = sortOrder.value === 'desc' ? -1 : 1
  
  switch (sortBy.value) {
    case 'amount':
      return list.sort((a, b) => ((b.amount || 0) - (a.amount || 0)) * order)
    case 'change':
      return list.sort((a, b) => (getChange(b) - getChange(a)) * order)
    case 'daily':
      return list.sort((a, b) => (getDailyProfit(b) - getDailyProfit(a)) * order)
    default:
      return list
  }
})

// 辅助方法
const getProfit = (holding) => {
  const fund = store.funds.find(f => f.fund_code === holding.code)
  const change = parseFloat(fund?.daily_change || 0) / 100
  return (holding.amount || 0) * change
}

const getChange = (holding) => {
  const fund = store.funds.find(f => f.fund_code === holding.code)
  return parseFloat(fund?.daily_change || 0)
}

const getDailyProfit = (holding) => {
  const fund = store.funds.find(f => f.fund_code === holding.code)
  const change = parseFloat(fund?.daily_change || 0) / 100
  return (holding.amount || 0) * change
}
const getNav = (holding) => {
  const fund = store.funds.find(f => f.fund_code === holding.code)
  return fund?.nav || '--'
}

const getEstNav = (holding) => {
  const fund = store.funds.find(f => f.fund_code === holding.code)
  return fund?.estimate_nav || '--'
}
const getHoldDays = (holding) => holding.buy_date ? Math.floor((Date.now() - new Date(holding.buy_date)) / 86400000) : 0

// 操作方法
const addHolding = async () => {
  if (!newHolding.value.code || !newHolding.value.amount) {
    alert('请填写基金代码和金额')
    return
  }
  
  const funds = [...store.holdings, { ...newHolding.value }]
  await store.saveHoldings(funds)
  
  newHolding.value = { code: '', amount: '' }
  showAdd.value = false
}

const updateHolding = async (holding) => {
  const funds = store.holdings.map(h => 
    h.code === holding.code ? holding : h
  )
  await store.saveHoldings(funds)
}

const removeHolding = async (code) => {
  if (!confirm('确定删除该持仓吗？')) return
  
  const funds = store.holdings.filter(h => h.code !== code)
  await store.saveHoldings(funds)
}

const handleClear = async () => {
  if (!confirm('确定清空所有持仓吗？')) return
  await store.saveHoldings([])
}

const handleExport = () => {
  const data = store.holdings.map(h => `${h.code},${h.name},${h.amount}`)
  const csv = '基金代码,基金名称,持仓金额\\n' + data.join('\\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'holdings.csv'
  a.click()
}

const triggerOCR = () => {
  showOCR.value = true
}

const handleOCRFile = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  
  // TODO: 实现OCR识别
  alert('OCR功能开发中')
  showOCR.value = false
}
</script>


<style scoped>
.holdings {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary { background: #3b82f6; color: white; }
.btn-primary:hover { background: #2563eb; }

.btn-secondary { background: #6b7280; color: white; }
.btn-secondary:hover { background: #4b5563; }

.btn-success { background: #10b981; color: white; }
.btn-success:hover { background: #059669; }

.btn-danger { background: #ef4444; color: white; }
.btn-danger:hover { background: #dc2626; }

/* 统计卡片 */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.summary-card {
  text-align: center;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
}

.summary-card.highlight {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.summary-card .label {
  display: block;
  font-size: 12px;
  margin-bottom: 8px;
  opacity: 0.8;
}

.summary-card .value {
  font-size: 24px;
  font-weight: bold;
}

.summary-card .value.up { color: #ef4444; }
.summary-card .value.down { color: #22c55e; }
.summary-card.highlight .value.up { color: #ff6b6b; }
.summary-card.highlight .value.down { color: #4ade80; }

/* 排序标签 */
.sort-tabs {
  display: flex;
  gap: 8px;
  background: #f3f4f6;
  padding: 4px;
  border-radius: 8px;
}

.sort-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sort-order {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  transition: all 0.2s;
}

.sort-order:hover {
  background: #f3f4f6;
  border-color: #3b82f6;
  color: #3b82f6;
}

.tab {
  flex: 1;
  padding: 8px 16px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.tab.active {
  background: white;
  color: #3b82f6;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* 持仓卡片 */
.holding-card {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.fund-info {
  display: flex;
  flex-direction: column;
}

.fund-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.fund-code {
  font-size: 12px;
  color: #999;
}

.btn-delete {
  width: 24px;
  height: 24px;
  border: none;
  background: #fee2e2;
  color: #ef4444;
  border-radius: 50%;
  cursor: pointer;
  font-size: 12px;
}

.card-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.stat {
  text-align: center;
}

.stat .label {
  display: block;
  font-size: 11px;
  color: #666;
  margin-bottom: 4px;
}

.stat .value {
  font-size: 16px;
  font-weight: 600;
}

.stat .value.up { color: #ef4444; }
.stat .value.down { color: #22c55e; }

.card-meta {
  display: flex;
  gap: 16px;
  padding: 8px 12px;
  background: #e5e7eb;
  border-radius: 6px;
  font-size: 12px;
  color: #666;
  margin-bottom: 12px;
}

.card-edit {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-edit input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.card-edit .unit {
  color: #666;
  font-size: 14px;
}

.btn-save {
  padding: 8px 16px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

/* 空状态 */
.empty {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty p {
  margin-bottom: 20px;
  font-size: 16px;
}

.empty-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

/* 弹窗 */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 24px;
  width: 90%;
  max-width: 400px;
}

.modal-content h2 {
  margin: 0 0 20px;
  font-size: 18px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 14px;
  color: #666;
  margin-bottom: 6px;
}

.form-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
}

.modal-actions button {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.modal-actions button:not(.primary) {
  background: #f3f4f6;
  color: #666;
}

.modal-actions button.primary {
  background: #3b82f6;
  color: white;
}

.ocr-area {
  text-align: center;
  padding: 40px 20px;
  border: 2px dashed #ddd;
  border-radius: 8px;
  margin: 20px 0;
}

.ocr-area input {
  margin-bottom: 10px;
}

@media (max-width: 768px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .card-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .btn {
    justify-content: center;
  }
}
</style>

