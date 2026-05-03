import { Bell, X } from 'lucide-react'
import { clsx } from 'clsx'
import { useMarketStore } from '../../stores/marketStore'
import type { Alert } from '../../types'

const ALERT_ICONS: Record<Alert['type'], string> = {
  level_approach: '🔔',
  regime_shift: '⚡',
  a_period_complete: '🎯',
  gap_update: '📊',
  macro_spike: '🌐',
  event_warning: '⚠️',
}

const SEVERITY_STYLES: Record<Alert['severity'], string> = {
  info: 'border-l-blue-400',
  warning: 'border-l-orange-400',
  critical: 'border-l-bear',
}

export function AlertsFeed() {
  const { alerts, dismissAlert } = useMarketStore()
  const visible = alerts.filter((a) => !a.dismissed).slice(0, 10)

  if (visible.length === 0) {
    return (
      <div className="atlas-card">
        <div className="flex items-center gap-2 mb-2">
          <Bell size={14} className="text-text-secondary" />
          <span className="text-[11px] uppercase tracking-wider text-text-secondary">Live Alerts</span>
        </div>
        <p className="text-sm text-text-secondary text-center py-4">
          No alerts. Monitoring active.
        </p>
      </div>
    )
  }

  return (
    <div className="atlas-card">
      <div className="flex items-center gap-2 mb-3">
        <Bell size={14} className="text-gold" />
        <span className="text-[11px] uppercase tracking-wider text-text-secondary">Live Alerts</span>
        <span className="ml-auto text-xs font-mono text-bull">{visible.length}</span>
      </div>
      <div className="space-y-2">
        {visible.map((alert) => (
          <AlertCard key={alert.id} alert={alert} onDismiss={() => dismissAlert(alert.id)} />
        ))}
      </div>
    </div>
  )
}

function AlertCard({ alert, onDismiss }: { alert: Alert; onDismiss: () => void }) {
  const timeAgo = getTimeAgo(alert.timestamp)
  return (
    <div className={clsx(
      'p-3 rounded-lg border-l-4 bg-bg animate-slide-in relative',
      SEVERITY_STYLES[alert.severity]
    )}>
      <div className="flex items-start gap-2 pr-6">
        <span className="text-base leading-none mt-0.5">{ALERT_ICONS[alert.type]}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-text-primary leading-relaxed">{alert.content}</p>
          <span className="text-[10px] text-text-secondary">{timeAgo}</span>
        </div>
      </div>
      <button
        onClick={onDismiss}
        className="absolute top-2 right-2 text-text-secondary hover:text-text-primary"
      >
        <X size={12} />
      </button>
    </div>
  )
}

function getTimeAgo(ts: string): string {
  const diff = (Date.now() - new Date(ts).getTime()) / 1000
  if (diff < 60) return `${Math.floor(diff)}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}
