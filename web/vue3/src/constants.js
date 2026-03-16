// 缓存配置
export const CACHE_CONFIG = {
  FUNDS_KEY: 'fund_daily_funds',
  EXPIRY: 10 * 60 * 1000 // 10分钟
}

// API 配置
export const API_CONFIG = {
  TIMEOUT: 10000,
  RETRY_COUNT: 3
}

// 评分阈值
export const SCORE_THRESHOLDS = {
  EXCELLENT: 70,
  GOOD: 50,
  FAIR: 30
}

// 排序配置
export const SORT_CONFIG = {
  AMOUNT: 'amount',
  CHANGE: 'change',
  DAILY: 'daily'
}
