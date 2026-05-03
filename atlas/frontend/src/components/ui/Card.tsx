import { clsx } from 'clsx'

interface CardProps {
  children: React.ReactNode
  className?: string
  title?: string
  titleRight?: React.ReactNode
  noPad?: boolean
}

export function Card({ children, className, title, titleRight, noPad }: CardProps) {
  return (
    <div className={clsx('atlas-card', className)}>
      {title && (
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-text-secondary">
            {title}
          </span>
          {titleRight && <div>{titleRight}</div>}
        </div>
      )}
      <div className={noPad ? '-m-4' : ''}>{children}</div>
    </div>
  )
}

export function MetricGrid({ children, cols = 2 }: { children: React.ReactNode; cols?: 2 | 3 | 4 }) {
  return (
    <div className={clsx('grid gap-3', {
      'grid-cols-2': cols === 2,
      'grid-cols-3': cols === 3,
      'grid-cols-4': cols === 4,
    })}>
      {children}
    </div>
  )
}

export function Metric({ label, value, sub, color }: {
  label: string
  value: React.ReactNode
  sub?: string
  color?: string
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wider text-text-secondary">{label}</span>
      <span className={clsx('text-lg font-mono font-semibold', color || 'text-text-primary')}>
        {value ?? '—'}
      </span>
      {sub && <span className="text-[11px] text-text-secondary">{sub}</span>}
    </div>
  )
}
