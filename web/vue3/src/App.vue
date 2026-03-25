<template>
  <div id="app">
    <header class="header">
      <div class="header-content">
        <h1>🦞 Fund Daily</h1>
        <span class="date">{{ currentDate }}</span>
      </div>
      <div class="user-bar">
        <template v-if="store.user">
          <span class="username">{{ store.user.username }}</span>
          <button @click="showSettings = true" title="设置">⚙️</button>
          <button @click="handleLogout">退出</button>
        </template>
        <button v-else @click="showLogin = true">登录</button>
      </div>
    </header>
    
    <!-- 全局错误提示 -->
    <div v-if="store.error" class="error-banner">
      <div class="error-content">
        <span class="error-icon">⚠️</span>
        <span class="error-message">{{ store.error }}</span>
        <button class="error-close" @click="clearError">×</button>
      </div>
    </div>
    
    <nav class="nav">
      <router-link to="/">首页</router-link>
      <router-link to="/holdings">持仓</router-link>
      <router-link to="/quant">量化</router-link>
      <router-link to="/analysis">分析</router-link>
    </nav>
    
    <main class="main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    
    <!-- Login/Register Modal -->
    <div v-if="showLogin" class="modal" @click.self="closeLogin">
      <div class="modal-content auth-modal">
        <h2>{{ isRegistering ? '📝 注册新账号' : '🔐 登录' }}</h2>
        
        <!-- 登录/注册 Tab 切换 -->
        <div class="auth-tabs">
          <button 
            :class="{ active: !isRegistering }" 
            @click="switchToLogin"
          >
            🔐 登录
          </button>
          <button 
            :class="{ active: isRegistering }" 
            @click="switchToRegister"
          >
            📝 注册
          </button>
        </div>
        
        <!-- 登录表单 -->
        <form v-if="!isRegistering" @submit.prevent="handleLogin" class="auth-form">
          <div class="form-group">
            <label>用户名</label>
            <input v-model="loginForm.username" placeholder="请输入用户名" required />
          </div>
          <div class="form-group">
            <label>密码</label>
            <input v-model="loginForm.password" type="password" placeholder="请输入密码" required @keyup.enter="handleLogin" />
          </div>
          <div class="modal-actions">
            <button type="button" @click="closeLogin">取消</button>
            <button type="submit" class="primary" :disabled="loggingIn">
              {{ loggingIn ? '登录中...' : '登录' }}
            </button>
          </div>
          <p class="auth-switch">
            没有账号？<a href="#" @click.prevent="switchToRegister">立即注册</a>
          </p>
        </form>
        
        <!-- 注册表单 -->
        <form v-else @submit.prevent="handleRegister" class="auth-form">
          <div class="form-group">
            <label>用户名</label>
            <input v-model="loginForm.username" placeholder="请输入用户名（至少3位）" required minlength="3" />
          </div>
          <div class="form-group">
            <label>密码</label>
            <input v-model="loginForm.password" type="password" placeholder="请输入密码（至少6位）" required minlength="6" />
          </div>
          <div class="form-group">
            <label>确认密码</label>
            <input v-model="loginForm.confirmPassword" type="password" placeholder="请再次输入密码" required @keyup.enter="handleRegister" />
          </div>
          <div class="modal-actions">
            <button type="button" @click="closeLogin">取消</button>
            <button type="submit" class="primary">注册</button>
          </div>
          <p class="auth-switch">
            已有账号？<a href="#" @click.prevent="switchToLogin">立即登录</a>
          </p>
        </form>
      </div>
    </div>
    
    <!-- Settings Modal -->
    <div v-if="showSettings" class="modal" @click.self="showSettings = false">
      <div class="modal-content settings-modal">
        <h2>⚙️ 设置</h2>
        
        <div class="settings-tabs">
          <button :class="{ active: settingsTab === 'notify' }" @click="settingsTab = 'notify'">通知</button>
          <button :class="{ active: settingsTab === 'account' }" @click="settingsTab = 'account'">账号</button>
        </div>
        
        <!-- Notification Settings -->
        <div v-if="settingsTab === 'notify'" class="settings-content">
          <h3>通知设置</h3>
          
          <div class="setting-item">
            <label class="toggle">
              <input type="checkbox" v-model="settings.dingtalk.enabled" />
              <span>钉钉通知</span>
            </label>
          </div>
          <div v-if="settings.dingtalk.enabled" class="setting-details">
            <input v-model="settings.dingtalk.webhook" placeholder="Webhook URL" />
          </div>
          
          <div class="setting-item">
            <label class="toggle">
              <input type="checkbox" v-model="settings.telegram.enabled" />
              <span>Telegram 通知</span>
            </label>
          </div>
          <div v-if="settings.telegram.enabled" class="setting-details">
            <input v-model="settings.telegram.bot_token" placeholder="Bot Token" />
            <input v-model="settings.telegram.chat_id" placeholder="Chat ID" />
          </div>
          
          <div class="setting-item">
            <label class="toggle">
              <input type="checkbox" v-model="settings.email.enabled" />
              <span>邮件通知</span>
            </label>
          </div>
          <div v-if="settings.email.enabled" class="setting-details">
            <input v-model="settings.email.smtp_server" placeholder="SMTP 服务器" />
            <input v-model.number="settings.email.smtp_port" type="number" placeholder="端口" />
            <input v-model="settings.email.username" placeholder="用户名" />
            <input v-model="settings.email.password" type="password" placeholder="密码" />
            <input v-model="settings.email.to_addr" placeholder="收件人" />
          </div>
          
          <div class="modal-actions">
            <button @click="showSettings = false">取消</button>
            <button class="primary" @click="saveSettings">保存</button>
          </div>
        </div>
        
        <!-- Account Settings -->
        <div v-if="settingsTab === 'account'" class="settings-content">
          <h3>账号信息</h3>
          <div class="account-info">
            <p><strong>用户名:</strong> {{ store.user?.username }}</p>
          </div>
          
          <h4>修改密码</h4>
          <div class="form-group">
            <input v-model="passwordForm.oldPassword" type="password" placeholder="当前密码" />
          </div>
          <div class="form-group">
            <input v-model="passwordForm.newPassword" type="password" placeholder="新密码" />
          </div>
          <div class="form-group">
            <input v-model="passwordForm.confirmPassword" type="password" placeholder="确认新密码" />
          </div>
          
          <div class="modal-actions">
            <button @click="showSettings = false">取消</button>
            <button class="primary" @click="changePassword">修改密码</button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Loading -->
    <div v-if="store.loading.funds || store.loading.advice" class="loading-overlay">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useFundStore } from '@/stores/fund'

interface LoginForm {
  username: string
  password: string
  confirmPassword: string
}

interface Settings {
  dingtalk: { enabled: boolean; webhook: string }
  telegram: { enabled: boolean; bot_token: string; chat_id: string }
  email: { enabled: boolean; smtp_server: string; smtp_port: number; username: string; password: string; to_addr: string }
}

const store = useFundStore()
const showLogin = ref(false)
const showSettings = ref(false)
const settingsTab = ref<'notify' | 'security'>('notify')
const isRegistering = ref(false)
const loginForm = ref<LoginForm>({ username: '', password: '', confirmPassword: '' })
const loggingIn = ref(false)

const settings = reactive<Settings>({
  dingtalk: { enabled: false, webhook: '' },
  telegram: { enabled: false, bot_token: '', chat_id: '' },
  email: { enabled: false, smtp_server: '', smtp_port: 587, username: '', password: '', to_addr: '' }
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const currentDate = computed<string>(() => {
  return new Date().toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  })
})

const switchToLogin = (): void => {
  isRegistering.value = false
  loginForm.value = { username: '', password: '', confirmPassword: '' }
}

const switchToRegister = (): void => {
  isRegistering.value = true
  loginForm.value = { username: '', password: '', confirmPassword: '' }
}

const closeLogin = (): void => {
  showLogin.value = false
  loginForm.value = { username: '', password: '', confirmPassword: '' }
}

const handleLogin = async (): Promise<void> => {
  if (loggingIn.value) return
  loggingIn.value = true
  try {
    const result = await store.login(loginForm.value.username, loginForm.value.password) as { success?: boolean; message?: string }
    if (result.success) {
      // 强制刷新一次数据并确保加载成功
      await Promise.all([
        store.fetchHoldings(),
        store.fetchFunds(true)
      ])
      showLogin.value = false
      loginForm.value = { username: '', password: '', confirmPassword: '' }
      loadSettings()
    } else {
      alert(result.message || '登录失败')
    }
  } finally {
    loggingIn.value = false
  }
}

const handleRegister = async (): Promise<void> => {
  const { username, password, confirmPassword } = loginForm.value

  if (!username || !password) {
    alert('用户名和密码不能为空')
    return
  }
  if (password.length < 6) {
    alert('密码长度至少6位')
    return
  }
  if (password !== confirmPassword) {
    alert('两次输入的密码不一致')
    return
  }

  try {
    const response = await fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
    const data = await response.json() as { success?: boolean; error?: { message?: string }; message?: string }

    if (data.success) {
      alert('注册成功！请使用新账号登录')
      isRegistering.value = false
      loginForm.value = { username: '', password: '', confirmPassword: '' }
    } else {
      alert(data.error?.message || data.message || '注册失败')
    }
  } catch (error) {
    alert('注册请求失败，请检查网络连接')
    console.error('Registration error:', error)
  }
}

const handleLogout = async (): Promise<void> => {
  await store.logout()
}

const loadSettings = async (): Promise<void> => {
  try {
    const res = await fetch('/api/config')
    const data = await res.json()
    if (data) {
      settings.dingtalk = { ...settings.dingtalk, ...data.dingtalk }
      settings.telegram = { ...settings.telegram, ...data.telegram }
      settings.email = { ...settings.email, ...data.email }
    }
  } catch (e) {
    console.error('Failed to load settings:', e)
  }
}

const saveSettings = async (): Promise<void> => {
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    })
    const data = await res.json() as { success?: boolean; message?: string }
    if (data.success) {
      alert('设置已保存')
      showSettings.value = false
    } else {
      alert(data.message || '保存失败')
    }
  } catch (e) {
    alert('保存失败')
  }
}

const changePassword = async (): Promise<void> => {
  if (!passwordForm.oldPassword || !passwordForm.newPassword) {
    alert('请填写完整')
    return
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    alert('两次密码不一致')
    return
  }

  try {
    const res = await fetch('/api/password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        old_password: passwordForm.oldPassword,
        new_password: passwordForm.newPassword
      })
    })
    const data = await res.json() as { success?: boolean; message?: string }
    if (data.success) {
      alert('密码修改成功')
      passwordForm.oldPassword = ''
      passwordForm.newPassword = ''
      passwordForm.confirmPassword = ''
    } else {
      alert(data.message || '修改失败')
    }
  } catch (e) {
    alert('修改失败')
  }
}

onMounted(async (): Promise<void> => {
  await store.checkLogin()
  if (store.user) {
    loadSettings()
  }
})

const clearError = (): void => {
  store.error = null
}
</script>

<style scoped>
.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h1 {
  margin: 0;
  font-size: 20px;
}

.header-content .date {
  font-size: 12px;
  opacity: 0.9;
}

.user-bar {
  display: flex;
  gap: 10px;
  align-items: center;
}

.user-bar .username {
  font-weight: 500;
}

.user-bar button {
  background: rgba(255,255,255,0.2);
  border: none;
  color: white;
  padding: 5px 12px;
  border-radius: 4px;
  cursor: pointer;
}

.nav {
  display: flex;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.nav a {
  flex: 1;
  padding: 12px;
  text-align: center;
  color: #666;
  text-decoration: none;
  border-bottom: 2px solid transparent;
}

.nav a.router-link-active {
  color: #667eea;
  border-bottom-color: #667eea;
}

.main {
  padding: 20px;
  width: 100%;
  max-width: 100%;
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
  width: 320px;
}

.settings-modal {
  width: 480px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-content h2 {
  margin-top: 0;
}

.form-group {
  margin-bottom: 12px;
}

.modal-content input {
  width: 100%;
  padding: 10px;
  margin-bottom: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

.modal-actions button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.modal-actions .primary {
  background: #667eea;
  color: white;
}

.settings-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.settings-tabs button {
  flex: 1;
  padding: 10px;
  background: #f3f4f6;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.settings-tabs button.active {
  background: #667eea;
  color: white;
}

.settings-content h3 {
  margin: 0 0 16px;
  font-size: 16px;
}

.settings-content h4 {
  margin: 16px 0 12px;
  font-size: 14px;
  color: #666;
}

.setting-item {
  margin-bottom: 12px;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.toggle input {
  width: auto;
  margin: 0;
}

.setting-details {
  margin-left: 24px;
  margin-top: 8px;
}

.setting-details input {
  width: 100%;
  margin-bottom: 8px;
}

.account-info {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  margin-bottom: 16px;
}

.account-info p {
  margin: 0;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255,255,255,0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* 错误提示样式 */
.error-banner {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  color: #856404;
  padding: 8px 16px;
  font-size: 14px;
}

.error-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1200px;
  margin: 0 auto;
}

.error-icon {
  margin-right: 8px;
}

.error-message {
  flex: 1;
}

.error-close {
  background: none;
  border: none;
  color: #856404;
  font-size: 18px;
  cursor: pointer;
  padding: 0 8px;
}

.error-close:hover {
  opacity: 0.7;
}

/* 登录注册模态框样式 */
.auth-modal {
  max-width: 400px;
}

.auth-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 2px solid #e9ecef;
  padding-bottom: 12px;
}

.auth-tabs button {
  flex: 1;
  padding: 10px 16px;
  border: none;
  background: #f8f9fa;
  color: #6c757d;
  border-radius: 6px 6px 0 0;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.auth-tabs button:hover {
  background: #e9ecef;
}

.auth-tabs button.active {
  background: #667eea;
  color: white;
}

.auth-form .form-group {
  margin-bottom: 16px;
}

.auth-form label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: #495057;
  font-weight: 500;
}

.auth-form input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.auth-form input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.modal-actions {
  margin-top: 20px;
}

.modal-actions button {
  padding: 10px 24px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.modal-actions button:not(.primary) {
  background: #f8f9fa;
  color: #6c757d;
  margin-right: 12px;
}

.modal-actions button:not(.primary):hover {
  background: #e9ecef;
}

.modal-actions button.primary {
  background: #667eea;
  color: white;
}

.modal-actions button.primary:hover {
  background: #5a67d8;
}

.auth-switch {
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
  color: #6c757d;
}

.auth-switch a {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
}

.auth-switch a:hover {
  text-decoration: underline;
}

/* ==================== 响应式设计 ==================== */

/* 平板设备 (768px 及以下) */
@media (max-width: 768px) {
  .header {
    flex-direction: column;
    align-items: flex-start;
    padding: 12px 16px;
  }
  
  .header-content {
    width: 100%;
    margin-bottom: 12px;
  }
  
  .user-bar {
    width: 100%;
    justify-content: flex-end;
  }
  
  .nav {
    flex-wrap: wrap;
  }
  
  .nav a {
    flex: 1 0 50%;
    padding: 10px;
    font-size: 14px;
  }
  
  .main {
    padding: 16px;
  }
  
  .modal-content {
    width: 90%;
    max-width: 400px;
    padding: 20px;
  }
  
  .settings-modal {
    width: 90%;
    max-width: 500px;
  }
}

/* 手机设备 (480px 及以下) */
@media (max-width: 480px) {
  .header {
    padding: 10px 12px;
  }
  
  .header-content h1 {
    font-size: 20px;
  }
  
  .header-content .date {
    font-size: 12px;
  }
  
  .nav a {
    flex: 1 0 100%;
    padding: 8px;
    font-size: 13px;
  }
  
  .main {
    padding: 12px;
  }
  
  .modal-content {
    width: 95%;
    padding: 16px;
  }
  
  .auth-modal {
    max-width: 100%;
  }
  
  .auth-tabs {
    flex-direction: column;
  }
  
  .auth-tabs button {
    border-radius: 6px;
    margin-bottom: 8px;
  }
  
  .modal-actions {
    flex-direction: column;
  }
  
  .modal-actions button {
    width: 100%;
  }
}

/* 超大屏幕 (1200px 及以上) */
@media (min-width: 1200px) {
  .main {
    max-width: 1200px;
    margin: 0 auto;
  }
}

/* 防止表格和内容溢出 */
.table-container,
.card,
.chart-container {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

/* 确保图片和图表响应式 */
img,
canvas,
.chart-container {
  max-width: 100%;
  height: auto;
}

/* 改善小屏幕上的表单输入 */
@media (max-width: 480px) {
  input,
  select,
  textarea {
    font-size: 16px; /* 防止iOS缩放 */
  }
  
  button {
    min-height: 44px; /* 提高触摸目标大小 */
  }
}
</style>
