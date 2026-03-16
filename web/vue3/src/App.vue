<template>
  <div id="app">
    <header class="header">
      <div class="header-content">
        <h1>🦞 Fund Daily</h1>
        <span class="date">{{ currentDate }}</span>
      </div>
      <div class="user-bar">
        <template v-if="store.user">
          <span>{{ store.user.username }}</span>
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
        <input v-model="loginForm.username" placeholder="用户名" />
        <input v-model="loginForm.password" type="password" placeholder="密码" @keyup.enter="handleLogin" />
        <div class="modal-actions">
          <button @click="showLogin = false">取消</button>
          <button class="primary" @click="handleLogin">登录</button>
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
import { ref, computed, onMounted } from 'vue'
import { useFundStore } from '@/stores/fund'

const store = useFundStore()
const showLogin = ref(false)
const loginForm = ref({ username: '', password: '' })

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
  } else {
    alert(result.message || '登录失败')
  }
}

const handleLogout = async () => {
  await store.logout()
}

onMounted(() => {
  store.loadAll()
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
  max-width: 1200px;
  margin: 0 auto;
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

.modal-content h2 {
  margin-top: 0;
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
