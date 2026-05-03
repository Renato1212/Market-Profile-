import { useEffect, useState } from 'react'
import { fetchUnusualActivity } from '../../lib/api'
import type { UnusualActivity } from '../../types'

export function UnusualActivityTable() {
  const [items, setItems] = useState<UnusualActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'call' | 'put'>('all')

  useEffect(() => {
    fetchUnusualActivity()
      .then((r) => setItems(r.data.unusual_activity ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = filter === 'all' ? items : items.filter((i) => i.type === filter)

  if (loading) return <div className="atlas-card h-48 animate-pulse" />

  return (
    <div className="atlas-card">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[11px] uppercase tracking-wider text-text-secondary">Unusual Options Activity</div>
        <div className="flex gap-1">
          {(['all', 'call', 'put'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2.5 py-1 text-xs rounded-lg transition-colors ${
                filter === f
                  ? f === 'call' ? 'bg-bull/20 text-bull' : f === 'put' ? 'bg-bear/20 text-bear' : 'bg-blue/20 text-blue'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {f.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="text-[10px] text-text-secondary mb-3">
        Vol/OI &gt; 3.0 · Premium &gt; $50K · SPY options chain
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-text-secondary text-center py-6">
          No unusual activity detected in current scan.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                {['Type', 'Strike', 'Exp', 'Volume', 'OI', 'Vol/OI', 'Premium', 'Flag'].map((h) => (
                  <th key={h} className="text-left py-2 px-2 text-[9px] uppercase tracking-wider text-text-secondary font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((item, i) => (
                <tr key={i} className="border-b border-border/40 hover:bg-surface/50">
                  <td className="py-2 px-2">
                    <span className={`font-mono font-semibold text-[11px] ${item.type === 'call' ? 'text-bull' : 'text-bear'}`}>
                      {item.type.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-2 px-2 font-mono">{item.strike}</td>
                  <td className="py-2 px-2 font-mono text-text-secondary">{item.expiration?.slice(5)}</td>
                  <td className="py-2 px-2 font-mono">{item.volume?.toLocaleString()}</td>
                  <td className="py-2 px-2 font-mono text-text-secondary">{item.oi?.toLocaleString()}</td>
                  <td className="py-2 px-2 font-mono text-gold">{item.vol_oi_ratio?.toFixed(1)}x</td>
                  <td className="py-2 px-2 font-mono">{item.premium != null ? `$${(item.premium / 1000).toFixed(0)}K` : '—'}</td>
                  <td className="py-2 px-2">
                    {item.institutional && (
                      <span className="text-[9px] bg-purple/20 text-purple rounded px-1.5 py-0.5">INST</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
