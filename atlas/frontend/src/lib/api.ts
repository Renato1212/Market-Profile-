import axios from 'axios'
import type {
  GEXDashboard, MarketSnapshot, LiveAPeriodState,
  GapCalculatorResult, VIXTermStructure
} from '../types'

const BASE = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: BASE,
  timeout: 15000,
})

// Gap Fill
export const fetchGapTables = (years = 10) => api.get(`/gap/tables?years=${years}`)
export const fetchGapCalculator = (params: Record<string, unknown>) =>
  api.get<GapCalculatorResult>('/gap/calculator', { params })
export const fetchTodayGap = () => api.get('/gap/today')
export const fetchHypothesisTests = () => api.get('/gap/hypothesis-tests')

// A Period
export const fetchLiveAPeriod = () => api.get<LiveAPeriodState>('/aperiod/live')
export const fetchAPeriodHistory = (years = 5, aType?: string) =>
  api.get('/aperiod/history', { params: { years, a_type: aType } })

// Options / GEX
export const fetchGEXDashboard = () => api.get<GEXDashboard>('/options/gex')
export const fetchPCRatio = () => api.get('/options/pc-ratio')
export const fetchUnusualActivity = () => api.get('/options/unusual-activity')
export const fetchTermStructure = () => api.get<VIXTermStructure>('/options/term-structure')

// Market Data
export const fetchMarketSnapshot = () => api.get<MarketSnapshot>('/data/snapshot')
export const fetchMacroData = () => api.get('/data/macro')
export const fetchCOTData = () => api.get('/data/cot')
export const fetchDailyOHLCV = (symbol = 'ES=F', years = 5) =>
  api.get(`/data/ohlcv/daily?symbol=${symbol}&years=${years}`)

// AI Copilot
export const fetchTodayBriefing = () => api.get('/ai/briefing/today')
export const sendChatMessage = (question: string, history: Array<{role: string; content: string}>) =>
  api.post('/ai/chat', { question, history })
export const fetchRecentAlerts = (limit = 20) => api.get(`/ai/alerts/recent?limit=${limit}`)

// Live
export const fetchLiveStatus = () => api.get('/live/status')
export const triggerRefresh = () => api.post('/live/refresh')
