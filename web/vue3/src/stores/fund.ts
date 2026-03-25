import { defineStore } from 'pinia'
import api, { setAuthToken, clearAuthToken } from '@/api'
import { CACHE_CONFIG } from '@/constants'
import type { Fund, Holding, Advice, Sector, NewsItem, User } from '@/types/api'

function getCachedFunds(): Fund[] | null {
  try {
    const cached = localStorage.getItem(CACHE_CONFIG.FUNDS_KEY)
    if (cached) {
      const { data, timestamp } = JSON.parse(cached)
      if (Date.now() - timestamp < CACHE_CONFIG.FUNDS_EXPIRY) {
        return data
      }
    }
  } catch (e) {
    console.error('Cache read error:', e)
  }
  return null
}

function setCachedFunds(data: Fund[]): void {
  try {
    localStorage.setItem(CACHE_CONFIG.FUNDS_KEY, JSON.stringify({
      data,
      timestamp: Date.now()
    }))
  } catch (e) {
    console.error('Cache write error:', e)
  }
}

interface LoadingState {
  funds: boolean
  holdings: boolean
  advice: boolean
  sectors: boolean
  news: boolean
  timing: boolean
  optimize: boolean
  rebalancing: boolean
}

export const useFundStore = defineStore('fund', {
  state: () => ({
    funds: [] as Fund[],
    holdings: [] as Holding[],
    advice: null as Advice | null,
    sectors: [] as Sector[],
    news: [] as NewsItem[],
    timingSignals: {} as Record<string, unknown>,
    portfolioOptimize: {} as Record<string, unknown>,
    rebalancing: {} as Record<string, unknown>,
    loading: {
      funds: false,
      holdings: false,
      advice: false,
      sectors: false,
      news: false,
      timing: false,
      optimize: false,
      rebalancing: false
    } as LoadingState,
    error: null as string | null,
    user: null as User | null
  }),

  getters: {
    totalAmount(): number {
      return this.holdings.reduce((sum, h) => sum + (h.amount || 0), 0)
    },
    hasHoldings(): boolean {
      return this.holdings.length > 0 && this.holdings.some(h => (h.amount || 0) > 0)
    }
  },

  actions: {
    async fetchFunds(force = false): Promise<void> {
      if (force) {
        try {
          localStorage.removeItem(CACHE_CONFIG.FUNDS_KEY)
        } catch (e) {
          console.error('Cache clear error:', e)
        }
      }

      if (!force) {
        const cached = getCachedFunds()
        if (cached) {
          this.funds = cached
          return
        }
      }

      this.loading.funds = true
      try {
        const data = await api.getFunds(force)
        this.funds = data.funds || []
        setCachedFunds(this.funds)
      } catch (e) {
        const err = e as { formatted?: { message?: string }; message?: string }
        this.error = err.formatted?.message || err.message || '获取基金数据失败'
        console.error('Failed to fetch funds:', e)
      } finally {
        this.loading.funds = false
      }
    },

    startPeriodicFetch(): void {
      setInterval(() => {
        this.fetchFunds(true)
      }, 10 * 60 * 1000)
    },

    async fetchHoldings(): Promise<void> {
      this.loading.holdings = true
      try {
        const data = await api.getHoldings()
        this.holdings = data.holdings || []

        for (const h of this.holdings) {
          if (!h.name || h.name === '') {
            try {
              const res = await api.getFundDetail(h.code) as { detail?: { fund_name?: string }; fund?: { name?: string } }
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
        const err = e as { formatted?: { message?: string }; message?: string }
        this.error = err.formatted?.message || err.message || '获取持仓数据失败'
        console.error('Failed to fetch holdings:', e)
      } finally {
        this.loading.holdings = false
      }
    },

    async fetchAdvice(): Promise<void> {
      this.loading.advice = true
      try {
        const data = await api.getAdvice()
        this.advice = data.advice || null
      } catch (e) {
        const err = e as { formatted?: { message?: string }; message?: string }
        this.error = err.formatted?.message || err.message || '获取投资建议失败'
        console.error('Failed to fetch advice:', e)
      } finally {
        this.loading.advice = false
      }
    },

    async fetchSectors(): Promise<void> {
      this.loading.sectors = true
      try {
        const data = await api.getSectors()
        this.sectors = data.sectors || []
      } catch (e) {
        const err = e as { formatted?: { message?: string }; message?: string }
        this.error = err.formatted?.message || err.message || '获取热点板块失败'
        console.error('Failed to fetch sectors:', e)
      } finally {
        this.loading.sectors = false
      }
    },

    async fetchNews(force = false): Promise<void> {
      if (!force) {
        const cached = localStorage.getItem(CACHE_CONFIG.NEWS_KEY)
        if (cached) {
          try {
            const { data, timestamp } = JSON.parse(cached)
            if (Date.now() - timestamp < CACHE_CONFIG.NEWS_EXPIRY) {
              this.news = data
              return
            }
          } catch (e) {
            console.error('News cache error:', e)
          }
        }
      }

      this.loading.news = true
      try {
        const data = await api.getNews()
        this.news = data.news || []
        localStorage.setItem(CACHE_CONFIG.NEWS_KEY, JSON.stringify({
          data: this.news,
          timestamp: Date.now()
        }))
      } catch (e) {
        const err = e as { formatted?: { message?: string }; message?: string }
        this.error = err.formatted?.message || err.message || '获取市场新闻失败'
        console.error('Failed to fetch news:', e)
      } finally {
        this.loading.news = false
      }
    },

    async fetchTimingSignals(): Promise<void> {
      this.loading.timing = true
      try {
        const res = await fetch('/api/quant/timing-signals')
        const data = await res.json()
        if (data.success) {
          this.timingSignals = data.data?.market_timing || {}
        }
      } catch (e) {
        console.error('Failed to fetch timing signals:', e)
      } finally {
        this.loading.timing = false
      }
    },

    async fetchPortfolioOptimize(): Promise<void> {
      this.loading.optimize = true
      try {
        const res = await fetch('/api/quant/portfolio-optimize')
        const data = await res.json()
        if (data.success) {
          this.portfolioOptimize = {
            allocations: data.data?.allocations || [],
            fund_count: data.data?.fund_count || 0
          }
        }
      } catch (e) {
        console.error('Failed to fetch portfolio optimize:', e)
      } finally {
        this.loading.optimize = false
      }
    },

    async fetchRebalancing(): Promise<void> {
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

    async checkLogin(): Promise<void> {
      try {
        const data = await api.checkLogin()
        if (data.logged_in) {
          this.user = { username: data.username || '' }
        } else {
          this.user = null
        }
      } catch {
        this.user = null
      }
    },

    async login(username: string, password: string): Promise<unknown> {
      const data = await api.login(username, password)
      if (data.success) {
        // 保存 JWT token
        if (data.access_token) {
          setAuthToken(data.access_token)
        }
        this.user = { username: data.username || username }
        this.error = null  // 清除之前的错误提示
        // 并行加载所有板块数据
        await Promise.all([
          this.fetchHoldings(),
          this.fetchFunds(true),
          this.fetchAdvice(),
          this.fetchSectors(),
          this.fetchNews(),
          this.fetchTimingSignals(),
          this.fetchPortfolioOptimize(),
          this.fetchRebalancing()
        ])
      }
      return data
    },

    async logout(): Promise<void> {
      try {
        await api.logout()
      } catch (e) {
        console.error('Logout failed:', e)
      }
      clearAuthToken()
      this.user = null
      this.error = null
      this.holdings = []
      this.timingSignals = {}
      this.portfolioOptimize = {}
      this.rebalancing = {}
    },

    async saveHoldings(funds: unknown[]): Promise<void> {
      await api.saveHoldings({ funds })
      await this.fetchHoldings()
      await this.fetchFunds(true)
    },

    async clearHoldings(): Promise<void> {
      await api.clearHoldings()
      this.holdings = []
    },

    async removeHolding(code: string): Promise<void> {
      await api.deleteHolding(code)
      await this.fetchHoldings()
    },

    async loadAll(): Promise<void> {
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
