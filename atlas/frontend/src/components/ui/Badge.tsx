import { clsx } from 'clsx'
import type { GexRegime, Confidence } from '../../types'

interface RegimeBadgeProps {
  regime: GexRegime
  size?: 'sm' | 'md' | 'lg'
}

export function RegimeBadge({ regime, size = 'md' }: RegimeBadgeProps) {
  const labels: Record<GexRegime, string> = {
    long: 'LONG GAMMA',
    short: 'SHORT GAMMA',
    neutral: 'NEUTRAL GAMMA',
  }
  const sizes = { sm: 'text-xs px-2 py-0.5', md: 'text-sm px-3 py-1', lg: 'text-base px-4 py-1.5' }

  return (
    <span className={clsx(
      'font-mono font-semibold rounded-full uppercase tracking-wider',
      regime === 'long' && 'regime-long',
      regime === 'short' && 'regime-short',
      regime === 'neutral' && 'regime-neutral',
      sizes[size]
    )}>
      {labels[regime]}
    </span>
  )
}

interface ConfidenceBadgeProps {
  confidence: Confidence
  n?: number
}

export function ConfidenceBadge({ confidence, n }: ConfidenceBadgeProps) {
  const icons: Record<Confidence, string> = {
    high: '🟢',
    medium: '🟡',
    low: '🔴',
    insufficient: '⚫',
  }
  return (
    <span className={clsx('text-xs font-mono', `conf-${confidence}`)}>
      {icons[confidence]} {confidence.toUpperCase()}{n !== undefined ? ` (N=${n})` : ''}
    </span>
  )
}

interface ChangeProps {
  value: number | null
  suffix?: string
  decimals?: number
  showPlus?: boolean
}

export function Change({ value, suffix = '', decimals = 2, showPlus = true }: ChangeProps) {
  if (value === null || value === undefined) return <span className="text-text-secondary">—</span>
  const pos = value > 0
  const zero = value === 0
  return (
    <span className={clsx('font-mono', pos ? 'change-positive' : zero ? 'change-neutral' : 'change-negative')}>
      {showPlus && pos ? '+' : ''}{value.toFixed(decimals)}{suffix}
    </span>
  )
}

export function StatLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[11px] uppercase tracking-wider font-medium text-text-secondary">
      {children}
    </span>
  )
}
