<template>
  <div class="holdings">
    <section class="section">
      <div class="section-header">
        <h2>💰 我的持仓</h2>
        <div class="actions">
          <button @click="showAdd = true" class="btn-primary">添加持仓</button>
          <button @click="handleClear" class="btn-danger">清仓</button>
        </div>
      </div>
      
      <div class="summary">
        <div class="summary-item">
          <span class="label">持仓总数</span>
          <span class="value">{{ store.holdings.length }}</span>
        </div>
        <div class="summary-item">
          <span class="label">持仓金额</span>
          <span class="value">¥{{ totalAmount.toFixed(2) }}</span>
        </div>
      </div>
      
      <div v-if="store.holdings.length === 0" class="empty">
        <p>暂无持仓</p>
        <button @click="showAdd = true" class="btn-primary">添加第一个持仓</button>
      </div>
      
      <div v-else class="holding-list">
        <div v-for="(holding, index) in store.holdings" :key="holding.code" class="holding-item">
          <div class="holding-info">
            <span class="code">{{ holding.code }}</span>
            <span class="name">{{ holding.name || '未知' }}</span>
          </div>
          <div class="holding-amount">
            <input 
              v-model.number="holding.amount" 
              type="number" 
              @change="updateHolding(holding)"
              placeholder="金额"
            />
            <span class="unit">元</span>
          </div>
          <div class="holding-actions">
            <button @click="removeHolding(index)" class="btn-icon">🗑️</button>
          </div>
        </div>
      </div>
    </section>
    
    <!-- 评分建议 -->
    <section v-if="advice" class="section">
      <h2>📊 持仓评分</h2>
      <div class="score-cards">
        <div v-for="fund in advice.funds" :key="fund.fund_code" class="score-card">
          <div class="score-header">
            <span class="name">{{ fund.fund_name?.substring(0, 10) }}</span>
            <span class="score" :class="getScoreClass(fund.score_100?.total_score)">
              {{ fund.score_100?.total_score || '--' }}分
            </span>
          </div>
          <div class="score-details">
            <div class="detail">
              <span>估值</span>
              <span>{{ fund.score_100?.details?.valuation?.score || 0 }}/25</span>
            </div>
            <div class="detail">
              <span>业绩</span>
              <span>{{ fund.score_100?.details?.performance?.score || 0 }}/25</span>
            </div>
            <div class="detail">
              <span>风控</span>
              <span>{{ fund.score_100?.details?.risk_control?.score || 0 }}/15</span>
            </div>
            <div class="detail">
              <span>动量</span>
              <span>{{ fund.score_100?.details?.momentum?.score || 0 }}/20</span>
            </div>
          </div>
        </div>
      </div>
    </section>
    
    <!-- Add Modal -->
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
import { ref, computed } from 'vue'
import { useFundStore } from '@/stores/fund'

const store = useFundStore()
const showAdd = ref(false)
const newHolding = ref({ code: '', amount: '' })

const totalAmount = computed(() => store.totalAmount)
const advice = computed(() => store.advice)

const getScoreClass = (score) => {
  if (!score) return ''
  if (score >= 70) return 'excellent'
  if (score >= 50) return 'good'
  if (score >= 30) return 'fair'
  return 'poor'
}

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

const removeHolding = async (index) => {
  if (!confirm('确定删除该持仓吗？')) return
  
  const funds = store.holdings.filter((_, i) => i !== index)
  await store.saveHoldings(funds)
}

const handleClear = async () => {
  if (!confirm('确定清仓所有持仓吗？此操作不可恢复！')) return
  await store.clearHoldings()
}
</script>

<style scoped>
.holdings {
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

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  margin: 0;
}

.actions {
  display: flex;
  gap: 10px;
}

button {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-danger {
  background: #ef4444;
  color: white;
}

.btn-icon {
  background: transparent;
  padding: 4px 8px;
}

.summary {
  display: flex;
  gap: 40px;
  margin-bottom: 20px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-item .label {
  font-size: 12px;
  color: #666;
}

.summary-item .value {
  font-size: 24px;
  font-weight: bold;
}

.empty {
  text-align: center;
  padding: 40px;
  color: #999;
}

.empty p {
  margin-bottom: 16px;
}

.holding-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.holding-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.holding-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.holding-info .code {
  font-size: 14px;
  color: #666;
}

.holding-info .name {
  font-size: 16px;
  font-weight: 500;
}

.holding-amount {
  display: flex;
  align-items: center;
  gap: 8px;
}

.holding-amount input {
  width: 120px;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
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
  padding: 24px;
  border-radius: 8px;
  width: 360px;
}

.modal-content h2 {
  margin-top: 0;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #666;
}

.form-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
