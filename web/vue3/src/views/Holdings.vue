<template>
  <div class="holdings">
    <!-- 持仓内容 -->
    <section class="section">
      <div class="section-header">
        <h2>📈 我的持仓</h2>
        <div class="actions">
          <button class="btn-primary" @click="showImport = true">导入持仓</button>
          <button class="btn-secondary" @click="refreshData">刷新</button>
          <button class="btn-danger" @click="confirmClearAll" v-if="store.holdings?.length">清仓</button>
        </div>
      </div>
      
      <!-- 摘要 -->
      <div class="summary">
        <div class="summary-item">
          <span class="label">基金数量</span>
          <span class="value">{{ store.holdings?.length || 0 }}</span>
        </div>
        <div class="summary-item">
          <span class="label">总金额</span>
          <span class="value">¥{{ totalAmount.toFixed(2) }}</span>
        </div>
      </div>
      
      <!-- 持仓列表 -->
      <div v-if="store.holdings?.length" class="holding-list">
        <div v-for="holding in store.holdings" :key="holding.code" class="holding-item">
          <div class="holding-info">
            <span class="code">{{ holding.code }}</span>
            <span class="name">{{ holding.name || '未知基金' }}</span>
            
            <!-- 基金数据 - 始终显示，即使数据不全 -->
            <div class="fund-data">
              <div class="fund-stats">
                <span class="stat-item">
                  <span class="stat-label">净值:</span>
                  <span class="stat-value">{{ getFundData(holding.code)?.nav || '--' }}</span>
                </span>
                <span class="stat-item">
                  <span class="stat-label">估值:</span>
                  <span class="stat-value">
                    {{ getFundData(holding.code)?.estimate_nav || '--' }}
                  </span>
                </span>
              </div>
              
              <div class="fund-stats">
                <span class="stat-item">
                  <span class="stat-label">板块涨幅:</span>
                  <span class="stat-value" :class="getSectorChangeClass(getFundData(holding.code)?.daily_change)">
                    <span v-if="getFundData(holding.code)?.daily_change !== undefined" class="change">
                      {{ getFundData(holding.code)?.daily_change > 0 ? '+' : '' }}{{ getFundData(holding.code)?.daily_change?.toFixed(2) }}%
                    </span>
                    <span v-else>--</span>
                  </span>
                </span>
                <span class="stat-item">
                  <span class="stat-label">当日收益:</span>
                  <span class="stat-value" :class="getProfitClass(calculateProfit(holding))">
                    ¥{{ calculateProfit(holding).toFixed(2) || '0.00' }}
                  </span>
                </span>
              </div>
            </div>
          </div>
          <div class="holding-amount">
            <input type="number" v-model.number="holding.amount" @change="updateHolding(holding)" />
            <span>元</span>
          </div>
        </div>
      </div>
      <div v-else class="empty">
        <p>暂无持仓数据</p>
        <div class="empty-actions">
          <button class="btn-primary" @click="showImport = true">导入持仓</button>
        </div>
      </div>
    </section>
    
    <!-- 导入模态框 -->
    <div v-if="showImport" class="modal-overlay" @click.self="showImport = false">
      <div class="modal">
        <div class="modal-header">
          <h3>导入持仓</h3>
          <button class="close-btn" @click="showImport = false">×</button>
        </div>
        <!-- 导入内容 -->
        <div class="import-tabs">
          <button class="tab-btn" :class="{ active: importTab === 'ocr' }" @click="importTab = 'ocr'">截图识别</button>
          <button class="tab-btn" :class="{ active: importTab === 'text' }" @click="importTab = 'text'">文本导入</button>
        </div>
        
        <div v-if="importTab === 'ocr'" class="import-form">
          <p class="hint">上传截图，OCR自动识别基金持仓</p>
          <input type="file" accept="image/*" @change="handleOcrFile" :disabled="ocrLoading" />
          <div v-if="ocrLoading" class="loading">识别中...</div>
          <div v-if="ocrResult.length > 0" class="ocr-result">
            <h4>识别结果：</h4>
            <div v-for="(fund, idx) in ocrResult" :key="idx" class="ocr-item">
              <input v-model="fund.code" placeholder="代码" />
              <input v-model.number="fund.amount" type="number" placeholder="金额" />
            </div>
            <div v-if="ocrLoading" class="loading">导入中...</div>
            <div v-else class="ocr-actions">
              <button class="secondary" @click="ocrResult = []">重新识别</button>
              <button class="primary" @click="confirmOcrImport">确认导入</button>
            </div>
          </div>
        </div>
        
        <div v-if="importTab === 'text'" class="import-form">
          <p class="hint">输入基金代码和金额（每行一个）</p>
          <textarea v-model="importText" placeholder="示例：&#10;000001 1000&#10;017042 2795.9" rows="6"></textarea>
          <div class="modal-actions">
            <button class="secondary" @click="showImport = false">取消</button>
            <button class="primary" @click="confirmTextImport">确认导入</button>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <!-- 清仓确认对话框 -->
  <div v-if="showClearConfirm" class="modal-overlay" @click.self="showClearConfirm = false">
    <div class="modal">
      <div class="modal-header">
        <h3>确认清仓</h3>
        <button class="close-btn" @click="showClearConfirm = false">×</button>
      </div>
      <div class="clear-confirm-content">
        <p class="warning-text">⚠️ 警告：这将删除所有持仓数据！</p>
        <p class="confirm-text">您确定要清空所有持仓吗？此操作不可撤销。</p>
        <div class="clear-summary">
          <p>当前持仓：</p>
          <ul>
            <li>基金数量：{{ store.holdings?.length || 0 }} 只</li>
            <li>总金额：¥{{ totalAmount.toFixed(2) }}</li>
          </ul>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showClearConfirm = false">取消</button>
          <button class="btn-danger" @click="clearAllHoldings">确认清仓</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useFundStore } from '@/stores/fund'

const store = useFundStore()
const showImport = ref(false)
const showClearConfirm = ref(false)
const importTab = ref('ocr')
const ocrLoading = ref(false)
const ocrResult = ref([])
const importText = ref('')

const totalAmount = computed(() => {
  return store.holdings?.reduce((sum, h) => sum + (h.amount || 0), 0) || 0
})

// 获取基金数据
const getFundData = (code) => {
  if (!store.funds?.length) return null
  return store.funds.find(f => f.fund_code === code)
}

// 计算当日收益
const calculateProfit = (holding) => {
  const fundData = getFundData(holding.code)
  if (!fundData || fundData.daily_change === undefined || !holding.amount) return 0
  
  // 当日收益 = 持仓金额 * 日涨跌幅
  return holding.amount * (fundData.daily_change / 100)
}

// 获取估值颜色类（绿色涨，红色跌）
const getValuationClass = (change) => {
  if (change === undefined) return ''
  return change > 0 ? 'text-up' : change < 0 ? 'text-down' : ''
}

// 获取板块涨幅颜色类（红色涨，绿色跌）
const getSectorChangeClass = (change) => {
  if (change === undefined) return ''
  // 红色代表涨，绿色代表跌
  return change > 0 ? 'text-down' : change < 0 ? 'text-up' : ''
}

// 获取收益颜色类（红色正收益，绿色负收益）
const getProfitClass = (profit) => {
  if (profit === undefined || profit === 0) return ''
  // 红色代表正收益，绿色代表负收益
  return profit > 0 ? 'text-down' : profit < 0 ? 'text-up' : ''
}

const refreshData = async () => {
  await store.fetchHoldings()
  await store.fetchFunds()
}

const handleOcrFile = async (event) => {
  // OCR 处理逻辑
}

const confirmOcrImport = async () => {
  // 导入逻辑
}

const confirmTextImport = async () => {
  // 文本导入逻辑
}

const updateHolding = async (holding) => {
  // 更新持仓逻辑
}

// 清仓功能
const confirmClearAll = () => {
  if (store.holdings?.length > 0) {
    showClearConfirm.value = true
  }
}

const clearAllHoldings = async () => {
  try {
    await store.clearHoldings()
    showClearConfirm.value = false
    // 可以添加成功提示
    console.log('清仓成功')
  } catch (error) {
    console.error('清仓失败:', error)
    // 可以添加错误提示
  }
}
</script>

<style scoped>
.holdings {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 16px;
  max-width: 1200px;
  margin: 0 auto;
}

.section {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 12px;
}

button {
  padding: 10px 20px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5a67d8;
  transform: translateY(-2px);
}

.btn-secondary {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
}

.btn-secondary:hover {
  background: #e2e8f0;
}

.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.summary-item {
  text-align: center;
  padding: 20px;
  background: #f8fafc;
  border-radius: 12px;
}

.summary-item .label {
  display: block;
  font-size: 13px;
  color: #64748b;
  margin-bottom: 8px;
}

.summary-item .value {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
}

.holding-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.holding-item {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  background: #f8fafc;
  border-radius: 12px;
}

.holding-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.holding-info .code {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}

.holding-info .name {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

/* 基金数据样式 */
.fund-data {
  margin-top: 8px;
}

.fund-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.stat-label {
  color: #64748b;
  font-weight: 500;
  min-width: 48px;
}

.stat-value {
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 2px;
}

.stat-value .change {
  font-size: 11px;
  font-weight: 500;
}

/* 涨跌颜色 */
.text-up {
  color: #22c55e;
}

.text-down {
  color: #ef4444;
}

.holding-amount {
  display: flex;
  align-items: center;
  gap: 12px;
}

.holding-amount input {
  width: 140px;
  padding: 10px 12px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 15px;
}

.empty {
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.empty p {
  margin-bottom: 20px;
  font-size: 16px;
}

.empty-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 20px;
  padding: 32px;
  width: 90%;
  max-width: 500px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 24px;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
}

.import-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  background: #f1f5f9;
  padding: 4px;
  border-radius: 10px;
}

.tab-btn {
  flex: 1;
  padding: 12px;
  background: transparent;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
}

.tab-btn.active {
  background: white;
  color: #667eea;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.import-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hint {
  color: #64748b;
  font-size: 14px;
  text-align: center;
  margin: 0;
}

.import-form input[type="file"],
.import-form textarea {
  padding: 12px 16px;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  font-size: 15px;
}

.ocr-result {
  margin-top: 20px;
  padding: 20px;
  background: #f8fafc;
  border-radius: 12px;
}

.ocr-result h4 {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
}

.ocr-item {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

.ocr-item input {
  padding: 10px 12px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
}

.ocr-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.ocr-actions button {
  flex: 1;
  padding: 12px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #667eea;
  font-size: 16px;
  font-weight: 500;
}

/* 清仓确认对话框样式 */
.clear-confirm-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.warning-text {
  color: #dc2626;
  font-size: 16px;
  font-weight: 600;
  text-align: center;
  margin: 0;
}

.confirm-text {
  color: #4b5563;
  font-size: 15px;
  text-align: center;
  margin: 0;
}

.clear-summary {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  padding: 16px;
}

.clear-summary p {
  margin: 0 0 8px 0;
  font-weight: 500;
  color: #7f1d1d;
}

.clear-summary ul {
  margin: 0;
  padding-left: 20px;
}

.clear-summary li {
  color: #4b5563;
  margin-bottom: 4px;
}

.btn-danger {
  background: #dc2626;
  color: white;
  border: none;
  border-radius: 10px;
  padding: 12px 24px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-danger:hover {
  background: #b91c1c;
}

.btn-danger:disabled {
  background: #fca5a5;
  cursor: not-allowed;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .holdings {
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
  
  .actions {
    width: 100%;
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .actions button {
    flex: 1;
    min-width: 120px;
    padding: 10px 16px;
    font-size: 13px;
  }
  
  .summary {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .summary-item {
    padding: 16px;
  }
  
  .summary-item .value {
    font-size: 24px;
  }
  
  .holding-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 16px;
  }
  
  .holding-info {
    width: 100%;
  }
  
  .fund-stats {
    flex-direction: column;
    gap: 8px;
  }
  
  .stat-item {
    justify-content: space-between;
    width: 100%;
  }
  
  .holding-amount {
    width: 100%;
  }
  
  .holding-amount input {
    width: 100%;
  }
  
  .modal {
    padding: 24px;
    width: 95%;
    border-radius: 16px;
  }
  
  .ocr-item {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

@media (max-width: 480px) {
  .holdings {
    padding: 8px;
  }
  
  .section {
    padding: 16px;
    border-radius: 12px;
  }
  
  .section-header h2 {
    font-size: 18px;
  }
  
  .summary {
    grid-template-columns: 1fr;
  }
  
  .actions button {
    min-width: 100px;
    padding: 8px 12px;
    font-size: 12px;
  }
  
  .modal {
    padding: 20px;
  }
  
  .import-tabs {
    flex-direction: column;
  }
  
  .tab-btn {
    padding: 10px;
  }
}
</style>
