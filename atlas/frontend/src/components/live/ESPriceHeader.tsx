import { useEffect, useState } from 'react'
import { Activity } from 'lucide-react'
import { clsx } from 'clsx'
import { useMarketStore } from '../../stores/marketStore'
import { RegimeBadge } from '../ui/Badge'
import { fetchMarketSnapshot } from '../../lib/api'

export function ESPriceHeader() {
  const { snapshot, setSnapshot, isConnected } = useMarketStore()
  const [pulse, setPulse] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetchMarketSnapshot()
        setSnapshot(res.data)
        setPulse(true)
        setTimeout(() => setPulse(false), 600)
      } catch {}
    }

    load()
    const interval = setInterval(load, 15000) // Poll every 15s
    return () => clearInterval(interval)
  }, [setSnapshot])

  const es = snapshot?.es
  const regime = snapshot?.gex_regime

  const now = new Date()
  const etTime = now.toLocaleTimeString('en-US', { timeZone: 'America/New_York', hour12: false })

  return (
    <div className="bg-surface border-b border-border px-4 py-3">
      <div className="flex items-center justify-between">
        {/* Logo + Time */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div className={clsx(
              'w-2 h-2 rounded-full',
              isConnected ? 'bg-bull live-indicator' : 'bg-text-secondary'
            )} />
            <span className="text-xs font-mono text-text-secondary">{etTime} ET</span>
          </div>
        </div>

        {/* ES Price */}
        <div className="flex flex-col items-center">
          <span className="text-[10px] uppercase tracking-wider text-text-secondary">ES FUTURES</span>
          <div className={clsx(
            'text-2xl font-mono font-bold transition-colors duration-300',
            pulse ? 'text-gold' : 'text-text-primary'
          )}>
            {es?.price ? es.price.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '—'}
          </div>
          <div className={clsx(
            'text-sm font-mono',
            (es?.change ?? 0) > 0 ? 'change-positive' : (es?.change ?? 0) < 0 ? 'change-negative' : 'change-neutral'
          )}>
            {es?.change != null
              ? `${es.change > 0 ? '+' : ''}${es.change.toFixed(2)}${
                  es.change_pct != null
                    ? ` (${es.change_pct > 0 ? '+' : ''}${es.change_pct.toFixed(2)}%)`
                    : ''
                }`
              : '—'}
          </div>
        </div>

        {/* Regime */}
        <div className="flex flex-col items-end gap-1">
          {regime ? (
            <RegimeBadge regime={regime} size="sm" />
          ) : (
            <span className="text-xs text-text-secondary">Loading...</span>
          )}
          <div className="flex items-center gap-1 text-[10px] text-text-secondary">
            <Activity size={10} />
            <span>LIVE</span>
          </div>
        </div>
      </div>
    </div>
  )
}
