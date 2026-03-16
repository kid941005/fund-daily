import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true  // 发送 cookies
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
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
