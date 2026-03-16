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
    
    <nav class="nav">
      <router-link to="/">首页</router-link>
      <router-link to="/holdings">持仓</router-link>
      <router-link to="/analysis">分析</router-link>
    </nav>
    
    <main class="main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    
    <!-- Login Modal -->
    <div v-if="showLogin" class="modal" @click.self="showLogin = false">
      <div class="modal-content">
        <h2>登录</h2>
        <div class="form-group">
          <input v-model="loginForm.username" placeholder="用户名" />
        </div>
        <div class="form-group">
          <input v-model="loginForm.password" type="password" placeholder="密码" @keyup.enter="handleLogin" />
        </div>
        <div class="modal-actions">
          <button @click="showLogin = false">取消</button>
          <button class="primary" @click="handleLogin">登录</button>
        </div>
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

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useFundStore } from '@/stores/fund'
import api from '@/api'

const store = useFundStore()
const showLogin = ref(false)
const showSettings = ref(false)
const settingsTab = ref('notify')
const loginForm = ref({ username: '', password: '' })

const settings = reactive({
  dingtalk: { enabled: false, webhook: '' },
  telegram: { enabled: false, bot_token: '', chat_id: '' },
  email: { enabled: false, smtp_server: '', smtp_port: 587, username: '', password: '', to_addr: '' }
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const currentDate = computed(() => {
  return new Date().toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric',
    weekday: 'long'
  })
})

const handleLogin = async () => {
  const result = await store.login(loginForm.value.username, loginForm.value.password)
  if (result.success) {
    showLogin.value = false
    loginForm.value = { username: '', password: '' }
    loadSettings()
  } else {
    alert(result.message || '登录失败')
  }
}

const handleLogout = async () => {
  await store.logout()
}

const loadSettings = async () => {
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

const saveSettings = async () => {
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    })
    const data = await res.json()
    if (data.success) {
      alert('设置已保存')
      showSettings.value = false
    } else {
      alert(data.message || '保存失败')
    }
  } catch (e) {
    alert('保存失败: ' + e.message)
  }
}

const changePassword = async () => {
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
    const data = await res.json()
    if (data.success) {
      alert('密码修改成功')
      passwordForm.oldPassword = ''
      passwordForm.newPassword = ''
      passwordForm.confirmPassword = ''
    } else {
      alert(data.message || '修改失败')
    }
  } catch (e) {
    alert('修改失败: ' + e.message)
  }
}

onMounted(async () => {
  // 检查登录状态
  await store.checkLogin()
  if (store.user) {
    loadSettings()
  }
})
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
</style>
