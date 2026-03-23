// API 类型定义

export interface ApiError {
  message: string
  code: string
  name: string
  details: Record<string, unknown>
  timestamp?: string
  fullResponse?: unknown
}

export interface FormattedError {
  message: string
  code: string
  name: string
  details: Record<string, unknown>
  timestamp?: string
  fullResponse?: unknown
}

// 统一错误对象（拦截器抛出）
export interface UnifiedError extends Error {
  formatted?: FormattedError
  original?: unknown
}

// 基金数据
export interface Fund {
  code: string
  name?: string
  netWorth?: number
  netWorthDate?: string
  dayGrowth?: number
  lastWeekGrowth?: number
  lastMonthGrowth?: number
  lastThreeMonthsGrowth?: number
  lastSixMonthsGrowth?: number
  lastYearGrowth?: number
 今年以来?: number
  ['今年来']?: number
  estimatedWorth?: number
  estimatedWorthDate?: string
  purchaseStart?: string
  purchaseEnd?: string
  redeemStatus?: string
  fundType?: string
  riskLevel?: string
}

// 持仓数据
export interface Holding {
  code: string
  name?: string
  amount?: number
  cost?: number
  fund_type?: string
}

// 建议数据
export interface Advice {
  type?: string
  message?: string
  funds?: FundAdvice[]
}

export interface FundAdvice {
  code: string
  name: string
  action: 'buy' | 'sell' | 'hold'
  reason?: string
  score?: number
}

// 市场数据
export interface Sector {
  name: string
  change: number
  volume?: number
  reason?: string
}

export interface NewsItem {
  title: string
  summary?: string
  url?: string
  time?: string
  source?: string
}

// 登录相关
export interface LoginResponse {
  success: boolean
  logged_in?: boolean
  username?: string
  message?: string
}

// 量化模块
export interface TimingSignals {
  market_timing?: Record<string, unknown>
}

export interface Allocation {
  code: string
  name: string
  target_weight: number
  current_weight: number
  action: 'buy' | 'sell' | 'hold'
  reason?: string
  score?: number
}

export interface PortfolioOptimize {
  allocations: Allocation[]
  fund_count: number
}

export interface RebalancingResult {
  current_holdings: Holding[]
  target_holdings: TargetHolding[]
  changes: RebalanceChange[]
}

export interface TargetHolding {
  code: string
  name: string
  current_amount: number
  target_amount: number
  action: 'buy' | 'sell' | 'hold'
  change_pct: number
  score?: number
}

export interface RebalanceChange {
  code: string
  name: string
  from: number
  to: number
  action: 'buy' | 'sell' | 'hold'
}

// 用户信息
export interface User {
  username: string
}

// API 响应结构
export interface FundsResponse {
  success: boolean
  funds: Fund[]
}

export interface HoldingsResponse {
  success: boolean
  holdings: Holding[]
}

export interface AdviceResponse {
  success: boolean
  advice: Advice
}

export interface SectorsResponse {
  success: boolean
  sectors: Sector[]
}

export interface NewsResponse {
  success: boolean
  news: NewsItem[]
}

export interface AnalysisResponse {
  success: boolean
  data: unknown
}
