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
    const { config, response: axiosResponse } = error
    
    // 格式化错误信息
    let formattedError = null
    
    if (axiosResponse) {
      // HTTP错误（4xx, 5xx）
      const data = axiosResponse.data || {}
      
      // 解析新的结构化错误格式
      if (data.error && typeof data.error === 'object' && data.error.message) {
        // 新格式：{ success: false, error: { code, name, message, details }, timestamp }
        formattedError = {
          message: data.error.message,
          code: data.error.code,
          name: data.error.name,
          details: data.error.details || {},
          timestamp: data.timestamp,
          fullResponse: data
        }
      } else if (data.error && typeof data.error === 'string') {
        // 旧格式：{ success: false, error: "错误消息" }
        formattedError = {
          message: data.error,
          code: 'UNKNOWN_ERROR',
          name: 'UNKNOWN_ERROR',
          details: {},
          fullResponse: data
        }
      } else if (data.message && typeof data.message === 'string') {
        // 其他可能的格式
        formattedError = {
          message: data.message,
          code: 'UNKNOWN_ERROR',
          name: 'UNKNOWN_ERROR',
          details: {},
          fullResponse: data
        }
      } else {
        // 默认：使用HTTP状态码信息
        const status = axiosResponse.status
        const statusText = axiosResponse.statusText || '未知错误'
        formattedError = {
          message: `请求失败: ${status} ${statusText}`,
          code: `HTTP_${status}`,
          name: statusText,
          details: { status, statusText },
          fullResponse: data
        }
      }
    } else {
      // 网络错误或无响应（如超时、连接断开）
      const isTimeout = error.code === 'ECONNABORTED'
      const message = isTimeout ? '请求超时，请检查网络连接' : '网络连接失败，请检查网络设置'
      
      formattedError = {
        message,
        code: isTimeout ? 'TIMEOUT_ERROR' : 'NETWORK_ERROR',
        name: isTimeout ? 'TIMEOUT' : 'NETWORK_ERROR',
        details: { originalError: error.message },
        fullResponse: null
      }
    }
    
    // 创建统一的错误对象
    const finalError = new Error(formattedError.message)
    finalError.formatted = formattedError
    finalError.original = error
    
    // 只有网络错误才重试（无响应或超时）
    if (!axiosResponse && config && config.retry) {
      // 设置重试次数
      config.retryCount = config.retryCount || 0
      
      // 如果重试次数超过限制
      if (config.retryCount >= CONFIG.retry) {
        return Promise.reject(finalError)
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
    
    // HTTP错误或其他错误，直接拒绝（不重试）
    return Promise.reject(finalError)
  }
)

export default {
  // 基金相关
  getFunds(force = false) {
    const params = force ? '?force=true' : ''
    return api.get(`/funds${params}`)
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
