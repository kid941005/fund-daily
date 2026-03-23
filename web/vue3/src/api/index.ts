import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type {
  FundsResponse,
  HoldingsResponse,
  AdviceResponse,
  SectorsResponse,
  NewsResponse,
  LoginResponse,
  AnalysisResponse,
  UnifiedError,
  FormattedError
} from '@/types/api'

// 请求配置
const CONFIG = {
  timeout: 30000,
  retry: 3,
  retryDelay: 1000
}

interface RetryConfig extends InternalAxiosRequestConfig {
  retryCount?: number
}

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true
})

// 请求拦截器
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

// 格式化错误
function formatError(error: AxiosError): FormattedError {
  const axiosResponse = error.response
  const data = axiosResponse?.data as Record<string, unknown> | undefined

  if (axiosResponse) {
    // HTTP错误（4xx, 5xx）
    if (data?.error && typeof data.error === 'object' && 'message' in data.error) {
      const err = data.error as Record<string, unknown>
      return {
        message: String(err.message ?? 'Unknown error'),
        code: String(err.code ?? 'UNKNOWN_ERROR'),
        name: String(err.name ?? 'UNKNOWN_ERROR'),
        details: (err.details as Record<string, unknown>) || {},
        timestamp: data.timestamp as string | undefined,
        fullResponse: data
      }
    } else if (typeof data?.error === 'string') {
      return {
        message: data.error,
        code: 'UNKNOWN_ERROR',
        name: 'UNKNOWN_ERROR',
        details: {},
        fullResponse: data
      }
    } else if (typeof data?.message === 'string') {
      return {
        message: data.message,
        code: 'UNKNOWN_ERROR',
        name: 'UNKNOWN_ERROR',
        details: {},
        fullResponse: data
      }
    } else {
      const status = axiosResponse.status
      const statusText = axiosResponse.statusText || '未知错误'
      return {
        message: `请求失败: ${status} ${statusText}`,
        code: `HTTP_${status}`,
        name: statusText,
        details: { status, statusText },
        fullResponse: data
      }
    }
  } else {
    // 网络错误
    const isTimeout = error.code === 'ECONNABORTED'
    const message = isTimeout ? '请求超时，请检查网络连接' : '网络连接失败，请检查网络设置'
    return {
      message,
      code: isTimeout ? 'TIMEOUT_ERROR' : 'NETWORK_ERROR',
      name: isTimeout ? 'TIMEOUT' : 'NETWORK_ERROR',
      details: { originalError: error.message },
      fullResponse: null
    }
  }
}

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError) => {
    const config = error.config as RetryConfig | undefined
    const formatted: FormattedError = formatError(error)

    const finalError: UnifiedError = new Error(formatted.message)
    finalError.formatted = formatted
    finalError.original = error

    // 网络错误才重试
    if (!error.response && config) {
      config.retryCount = config.retryCount || 0

      if (config.retryCount >= CONFIG.retry) {
        return Promise.reject(finalError)
      }

      config.retryCount += 1

      return new Promise((resolve) => {
        setTimeout(() => {
          resolve(api(config))
        }, CONFIG.retryDelay)
      })
    }

    return Promise.reject(finalError)
  }
)

// API 方法
export default {
  // 基金相关
  getFunds(force = false): Promise<FundsResponse> {
    const params = force ? '?force=true' : ''
    return api.get(`/funds${params}`)
  },

  getFundDetail(code: string): Promise<unknown> {
    return api.get(`/fund-detail/${code}`)
  },

  // 持仓相关
  getHoldings(): Promise<HoldingsResponse> {
    return api.get('/holdings')
  },

  saveHoldings(data: { funds: unknown[] }): Promise<unknown> {
    return api.post('/holdings', data)
  },

  deleteHolding(code: string): Promise<unknown> {
    return api.delete('/holdings', { data: { code } })
  },

  clearHoldings(): Promise<unknown> {
    return api.post('/holdings/clear')
  },

  // 建议相关
  getAdvice(): Promise<AdviceResponse> {
    return api.get('/advice')
  },

  // 市场数据
  getSectors(limit = 10): Promise<SectorsResponse> {
    return api.get(`/sectors?limit=${limit}`)
  },

  getNews(limit = 8): Promise<NewsResponse> {
    return api.get(`/news?limit=${limit}`)
  },

  // 认证
  login(username: string, password: string): Promise<LoginResponse> {
    return api.post('/login', { username, password })
  },

  logout(): Promise<unknown> {
    return api.post('/logout')
  },

  checkLogin(): Promise<LoginResponse> {
    return api.get('/check-login')
  },

  // 评分
  getScore(code: string): Promise<unknown> {
    return api.get(`/score/${code}`)
  },

  getAnalysis(): Promise<AnalysisResponse> {
    return api.get('/analysis/portfolio')
  }
}
