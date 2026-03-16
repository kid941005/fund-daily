import axios from 'axios'

// 请求配置
const CONFIG = {
  timeout: 30000,
  retry: 3,
  retryDelay: 1000
}

const api = axios.create({
  baseURL: '/api',
  timeout: CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true
})

// 请求拦截器
api.interceptors.request.use(
  config => config,
  error => Promise.reject(error)
)

// 响应拦截器 - 统一错误处理
api.interceptors.response.use(
  response => response.data,
  error => {
    const { config, response } = error
    
    // 如果没有配置或不允许重试，则直接拒绝
    if (!config || !config.retry) {
      return Promise.reject(error)
    }
    
    // 设置重试次数
    config.retryCount = config.retryCount || 0
    
    // 如果重试次数超过限制
    if (config.retryCount >= CONFIG.retry) {
      return Promise.reject(error)
    }
    
    // 重试次数 +1
    config.retryCount += 1
    
    // 延迟后重新请求
    return new Promise(resolve => {
      setTimeout(() => {
        resolve(api(config))
      }, CONFIG.retryDelay)
    })
  }
)

export default {
  // 基金相关
  getFunds() {
    return api.get('/funds')
  },
  getFundDetail(code) {
    return api.get(`/fund-detail/${code}`)
  },
  
  // 持仓相关
  getHoldings() {
    return api.get('/holdings')
  },
  saveHoldings(data) {
    return api.post('/holdings', data)
  },
  deleteHolding(code) {
    return api.delete('/holdings', { data: { code } })
  },
  clearHoldings() {
    return api.post('/holdings/clear')
  },
  
  // 建议相关
  getAdvice() {
    return api.get('/advice')
  },
  
  // 市场数据
  getSectors(limit = 10) {
    return api.get(`/sectors?limit=${limit}`)
  },
  getNews(limit = 8) {
    return api.get(`/news?limit=${limit}`)
  },
  
  // 认证
  login(username, password) {
    return api.post('/login', { username, password })
  },
  logout() {
    return api.post('/logout')
  },
  checkLogin() {
    return api.get('/check-login')
  },
  
  // 评分
  getScore(code) {
    return api.get(`/score/${code}`)
  },
  
  getAnalysis() {
    return api.get('/analysis/portfolio')
  }
}
