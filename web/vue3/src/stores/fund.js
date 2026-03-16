import { defineStore } from 'pinia'
import api from '@/api'

// 缓存配置
const CACHE_KEY = 'fund_daily_funds'
const CACHE_EXPIRY = 10 * 60 * 1000 // 10分钟

function getCachedFunds() {
  try {
    const cached = localStorage.getItem(CACHE_KEY)
    if (cached) {
      const { data, timestamp } = JSON.parse(cached)
      if (Date.now() - timestamp < CACHE_EXPIRY) {
        return data
      }
    }
  } catch (e) {
    console.error('Cache read error:', e)
  }
  return null
}

function setCachedFunds(data) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({
      data,
      timestamp: Date.now()
    }))
  } catch (e) {
    console.error('Cache write error:', e)
  }
}

export const useFundStore = defineStore('fund', {
  state: () => ({
    funds: [],
    holdings: [],
    advice: null,
    sectors: [],
    news: [],
    timingSignals: {},
    portfolioOptimize: {},
    rebalancing: {},
    loading: {
      funds: false,
      holdings: false,
      advice: false,
      sectors: false,
      news: false,
      timing: false,
      optimize: false,
      rebalancing: false
    },
    error: null,
    user: null
  }),
  
  getters: {
    totalAmount: (state) => {
      return state.holdings.reduce((sum, h) => sum + (h.amount || 0), 0)
    },
    hasHoldings: (state) => {
      return state.holdings.length > 0 && state.holdings.some(h => h.amount > 0)
    }
  },
  
  actions: {
    async fetchFunds(force = false) {
      // 优先从本地缓存读取
      if (!force) {
        const cached = getCachedFunds()
        if (cached) {
          this.funds = cached
          return
        }
      }
      
      // 缓存过期或强制刷新，从API获取
      this.loading.funds = true
      try {
        const data = await api.getFunds()
        this.funds = data.funds || []
        setCachedFunds(this.funds)
      } catch (e) {
        this.error = e.message
        console.error('Failed to fetch funds:', e)
      } finally {
        this.loading.funds = false
      }
    },
    
    // 定时刷新（后台每10分钟）
    startPeriodicFetch() {
      setInterval(() => {
        this.fetchFunds(true)
      }, 10 * 60 * 1000)
    },
    
    async fetchHoldings() {
      this.loading.holdings = true
      try {
        const data = await api.getHoldings()
        this.holdings = data.holdings || []
        
        // 自动获取缺失的基金名称
        for (const h of this.holdings) {
          if (!h.name || h.name === '') {
            try {
              const res = await api.getFundDetail(h.code)
              // API 返回格式: { success, detail: { fund_name } }
              const fundName = res.detail?.fund_name || res.fund?.name
              if (fundName) {
                h.name = fundName
              }
            } catch (e) {
              console.error('Failed to fetch fund name:', e)
            }
          }
        }
      } catch (e) {
        console.error('Failed to fetch holdings:', e)
      } finally {
        this.loading.holdings = false
      }
    },
    
    async fetchAdvice() {
      this.loading.advice = true
      try {
        const data = await api.getAdvice()
        this.advice = data.advice || null
      } catch (e) {
        console.error('Failed to fetch advice:', e)
      } finally {
        this.loading.advice = false
      }
    },
    
    async fetchSectors() {
      this.loading.sectors = true
      try {
        const data = await api.getSectors()
        this.sectors = data.sectors || []
      } catch (e) {
        console.error('Failed to fetch sectors:', e)
      } finally {
        this.loading.sectors = false
      }
    },
    
    async fetchNews() {
      this.loading.news = true
      try {
        const data = await api.getNews()
        this.news = data.news || []
      } catch (e) {
        console.error('Failed to fetch news:', e)
      } finally {
        this.loading.news = false
      }
    },
    
    // 量化模块
    async fetchTimingSignals() {
      this.loading.timing = true
      try {
        const res = await fetch('/api/quant/timing-signals')
        const data = await res.json()
        if (data.success) {
          this.timingSignals = data.data || {}
        }
      } catch (e) {
        console.error('Failed to fetch timing signals:', e)
      } finally {
        this.loading.timing = false
      }
    },
    
    async fetchPortfolioOptimize() {
      this.loading.optimize = true
      try {
        const res = await fetch('/api/quant/portfolio-optimize')
        const data = await res.json()
        if (data.success) {
          this.portfolioOptimize = data.data || {}
        }
      } catch (e) {
        console.error('Failed to fetch portfolio optimize:', e)
      } finally {
        this.loading.optimize = false
      }
    },
    
    async fetchRebalancing() {
      this.loading.rebalancing = true
      try {
        const res = await fetch('/api/quant/rebalancing')
        const data = await res.json()
        if (data.success) {
          this.rebalancing = data.data || {}
        }
      } catch (e) {
        console.error('Failed to fetch rebalancing:', e)
      } finally {
        this.loading.rebalancing = false
      }
    },
    
    async checkLogin() {
      try {
        const data = await api.checkLogin()
        // API 返回: { logged_in, username }
        if (data.logged_in) {
          this.user = { username: data.username }
        } else {
          this.user = null
        }
      } catch (e) {
        this.user = null
      }
    },
    
    async login(username, password) {
      const data = await api.login(username, password)
      if (data.success) {
        this.user = { username: data.username }
        await this.fetchHoldings()
      }
      return data
    },
    
    async logout() {
      await api.logout()
      this.user = null
      this.holdings = []
    },
    
    async saveHoldings(funds) {
      await api.saveHoldings({ funds })
      await this.fetchHoldings()
    },
    
    async clearHoldings() {
      await api.clearHoldings()
      this.holdings = []
    },
    
    async loadAll() {
      await Promise.all([
        this.fetchFunds(),
        this.fetchHoldings(),
        this.fetchAdvice(),
        this.fetchSectors(),
        this.fetchNews(),
        this.checkLogin()
      ])
    }
  }
})
