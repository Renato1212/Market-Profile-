import { create } from 'zustand'
import type { MarketSnapshot, GEXDashboard, LiveAPeriodState, Alert } from '../types'

interface MarketStore {
  snapshot: MarketSnapshot | null
  gex: GEXDashboard | null
  aPeriod: LiveAPeriodState | null
  alerts: Alert[]
  lastUpdate: string | null
  isConnected: boolean

  setSnapshot: (s: MarketSnapshot) => void
  setGex: (g: GEXDashboard) => void
  setAPeriod: (a: LiveAPeriodState) => void
  addAlert: (alert: Alert) => void
  dismissAlert: (id: string) => void
  setConnected: (v: boolean) => void
}

export const useMarketStore = create<MarketStore>((set) => ({
  snapshot: null,
  gex: null,
  aPeriod: null,
  alerts: [],
  lastUpdate: null,
  isConnected: false,

  setSnapshot: (snapshot) => set({ snapshot, lastUpdate: new Date().toISOString() }),
  setGex: (gex) => set({ gex }),
  setAPeriod: (aPeriod) => set({ aPeriod }),
  addAlert: (alert) => set((state) => ({
    alerts: [alert, ...state.alerts.slice(0, 49)], // Keep last 50
  })),
  dismissAlert: (id) => set((state) => ({
    alerts: state.alerts.map((a) => a.id === id ? { ...a, dismissed: true } : a),
  })),
  setConnected: (isConnected) => set({ isConnected }),
}))
