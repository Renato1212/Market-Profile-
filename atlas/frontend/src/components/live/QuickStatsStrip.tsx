import { useEffect, useState } from 'react'
import { fetchMarketSnapshot, fetchPCRatio } from '../../lib/api'
import { RegimeBadge } from '../ui/Badge'

interface StatPill {
  label: string
  value: string
  color?: string
}

export function QuickStatsStrip() {
  const [stats, setStats] = useState<StatPill[]>([])

  useEffect(() => {
    const load = async () => {
      try {
        const [snapRes, pcRes] = await Promise.allSettled([fetchMarketSnapshot(), fetchPCRatio()])
        const snap = snapRes.status === 'fulfilled' ? snapRes.value.data : null
        const pc = pcRes.status === 'fulfilled' ? pcRes.value.data : null

        const pills: StatPill[] = []

        if (snap?.vix?.vix) {
          const v = snap.vix.vix
          pills.push({ label: 'VIX', value: `${v.current?.toFixed(2)} ${v.change > 0 ? '▲' : '▼'}`, color: v.change > 0 ? '#FF3855' : '#10D982' })
        }
        if (snap?.vix?.vvix) {
          pills.push({ label: 'VVIX', value: snap.vix.vvix.current?.toFixed(1) })
        }
        if (snap?.crypto?.btc) {
          const btc = snap.crypto.btc
          pills.push({ label: 'BTC', value: `${btc.change_pct > 0 ? '+' : ''}${btc.change_pct?.toFixed(1)}%`, color: btc.change_pct > 0 ? '#10D982' : '#FF3855' })
        }
        if (snap?.dxy) {
          pills.push({ label: 'DXY', value: snap.dxy.current?.toFixed(2) })
        }
        if (snap?.gex_regime) {
          pills.push({ label: 'GEX', value: snap.gex_regime.toUpperCase(), color: snap.gex_regime === 'long' ? '#10D982' : snap.gex_regime === 'short' ? '#FF3855' : '#FF8C42' })
        }
        if (pc?.latest) {
          pills.push({ label: 'P/C', value: pc.latest?.toFixed(3), color: pc.latest > 1.0 ? '#10D982' : pc.latest < 0.70 ? '#FF3855' : '#6B7B95' })
        }

        setStats(pills)
      } catch {}
    }

    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [])

  if (stats.length === 0) return null

  return (
    <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
      {stats.map((s) => (
        <div key={s.label} className="flex-shrink-0 bg-surface border border-border rounded-lg px-3 py-1.5 flex flex-col items-center">
          <span className="text-[9px] uppercase tracking-wider text-text-secondary">{s.label}</span>
          <span className="text-xs font-mono font-semibold" style={{ color: s.color || '#E8EDF7' }}>{s.value}</span>
        </div>
      ))}
    </div>
  )
}
