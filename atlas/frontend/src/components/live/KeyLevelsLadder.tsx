import { clsx } from 'clsx'
import { useMarketStore } from '../../stores/marketStore'

interface Level {
  label: string
  value: number
  color: string
  dash?: boolean
}

export function KeyLevelsLadder() {
  const { snapshot, gex } = useMarketStore()
  const esPrice = snapshot?.es?.price

  const levels: Level[] = [
    gex?.call_wall_es && { label: 'Call Wall', value: gex.call_wall_es, color: '#FFB800' },
    gex?.zero_gamma_es && { label: 'Zero Gamma', value: gex.zero_gamma_es, color: '#FF8C42', dash: true },
    gex?.put_wall_es && { label: 'Put Wall', value: gex.put_wall_es, color: '#00E5A0' },
  ].filter(Boolean) as Level[]

  if (!esPrice || levels.length === 0) {
    return (
      <div className="atlas-card text-center py-6 text-text-secondary text-sm">
        Key levels loading...
      </div>
    )
  }

  const allValues = [...levels.map((l) => l.value), esPrice]
  const min = Math.min(...allValues) - 10
  const max = Math.max(...allValues) + 10
  const range = max - min

  const getYPct = (val: number) => ((max - val) / range) * 100

  const sortedLevels = [...levels].sort((a, b) => b.value - a.value)

  return (
    <div className="atlas-card">
      <div className="text-[11px] uppercase tracking-wider text-text-secondary mb-3">Key Levels</div>
      <div className="relative" style={{ height: 240 }}>
        {/* Level lines */}
        {sortedLevels.map((level) => {
          const yPct = getYPct(level.value)
          return (
            <div
              key={level.label}
              className="absolute left-0 right-0 flex items-center gap-2"
              style={{ top: `${yPct}%`, transform: 'translateY(-50%)' }}
            >
              <div
                className={clsx('flex-1 border-t', level.dash ? 'border-dashed' : 'border-solid')}
                style={{ borderColor: level.color }}
              />
              <span className="text-[10px] font-mono whitespace-nowrap" style={{ color: level.color }}>
                {level.label}
              </span>
              <span className="text-[10px] font-mono" style={{ color: level.color }}>
                {level.value.toFixed(2)}
              </span>
            </div>
          )
        })}

        {/* Current ES price marker */}
        <div
          className="absolute left-0 right-0 flex items-center gap-2 z-10"
          style={{ top: `${getYPct(esPrice)}%`, transform: 'translateY(-50%)' }}
        >
          <div className="flex-1 border-t-2 border-text-primary" />
          <div className="bg-text-primary text-bg text-[10px] font-mono font-bold px-1.5 py-0.5 rounded">
            {esPrice.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Level legend */}
      <div className="mt-3 pt-3 border-t border-border flex flex-wrap gap-3">
        <LegendItem color="#FFB800" label="Call Wall (resist)" />
        <LegendItem color="#00E5A0" label="Put Wall (support)" />
        <LegendItem color="#FF8C42" label="Zero Gamma" dash />
      </div>
    </div>
  )
}

function LegendItem({ color, label, dash }: { color: string; label: string; dash?: boolean }) {
  return (
    <div className="flex items-center gap-1.5">
      <div
        className={clsx('w-6 h-0.5', dash ? 'border-dashed border-t' : '')}
        style={{ background: dash ? 'transparent' : color, borderColor: color }}
      />
      <span className="text-[10px] text-text-secondary">{label}</span>
    </div>
  )
}
