import { useState } from 'react'
import { fetchGapCalculator } from '../../lib/api'
import { ConfidenceBadge } from '../ui/Badge'
import type { GapCalculatorResult } from '../../types'

export function GapCalculator() {
  const [direction, setDirection] = useState<'up' | 'down'>('up')
  const [sizePts, setSizePts] = useState('8')
  const [vix, setVix] = useState('')
  const [dow, setDow] = useState('')
  const [regime, setRegime] = useState('')
  const [result, setResult] = useState<GapCalculatorResult | null>(null)
  const [loading, setLoading] = useState(false)

  const compute = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = {
        direction,
        size_pts: parseFloat(sizePts) || 0,
      }
      if (vix) params.vix = parseFloat(vix)
      if (dow) params.day_of_week = parseInt(dow)
      if (regime) params.regime = regime

      const res = await fetchGapCalculator(params)
      setResult(res.data)
    } catch {} finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="atlas-card">
        <div className="text-[11px] uppercase tracking-wider text-text-secondary mb-4">Gap Fill Probability Calculator</div>
        <div className="grid grid-cols-2 gap-3 mb-4">
          {/* Direction */}
          <div>
            <label className="text-[10px] uppercase tracking-wider text-text-secondary block mb-1">Direction</label>
            <div className="flex rounded-lg overflow-hidden border border-border">
              {(['up', 'down'] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setDirection(d)}
                  className={`flex-1 py-1.5 text-xs font-mono font-semibold transition-colors ${
                    direction === d
                      ? d === 'up' ? 'bg-bull text-bg' : 'bg-bear text-bg'
                      : 'text-text-secondary hover:text-text-primary'
                  }`}
                >
                  {d === 'up' ? '▲ GAP UP' : '▼ GAP DOWN'}
                </button>
              ))}
            </div>
          </div>
          {/* Size */}
          <div>
            <label className="text-[10px] uppercase tracking-wider text-text-secondary block mb-1">Gap Size (pts)</label>
            <input
              type="number"
              value={sizePts}
              onChange={(e) => setSizePts(e.target.value)}
              className="w-full bg-bg border border-border rounded-lg px-3 py-1.5 text-sm font-mono text-text-primary outline-none focus:border-blue"
              step="0.25" min="0.25"
            />
          </div>
          {/* VIX */}
          <div>
            <label className="text-[10px] uppercase tracking-wider text-text-secondary block mb-1">VIX Level (optional)</label>
            <input
              type="number"
              value={vix}
              onChange={(e) => setVix(e.target.value)}
              placeholder="e.g. 18.5"
              className="w-full bg-bg border border-border rounded-lg px-3 py-1.5 text-sm font-mono text-text-primary outline-none focus:border-blue placeholder-text-secondary"
            />
          </div>
          {/* Day of Week */}
          <div>
            <label className="text-[10px] uppercase tracking-wider text-text-secondary block mb-1">Day of Week</label>
            <select
              value={dow}
              onChange={(e) => setDow(e.target.value)}
              className="w-full bg-bg border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary outline-none focus:border-blue"
            >
              <option value="">Any Day</option>
              <option value="0">Monday</option>
              <option value="1">Tuesday</option>
              <option value="2">Wednesday</option>
              <option value="3">Thursday</option>
              <option value="4">Friday</option>
            </select>
          </div>
          {/* Regime */}
          <div className="col-span-2">
            <label className="text-[10px] uppercase tracking-wider text-text-secondary block mb-1">Trend Regime</label>
            <select
              value={regime}
              onChange={(e) => setRegime(e.target.value)}
              className="w-full bg-bg border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary outline-none focus:border-blue"
            >
              <option value="">Any Regime</option>
              <option value="bull">Bull Market</option>
              <option value="bear">Bear Market</option>
              <option value="mixed">Mixed</option>
            </select>
          </div>
        </div>

        <button
          onClick={compute}
          disabled={loading || !sizePts}
          className="w-full py-2.5 bg-blue text-bg font-semibold rounded-xl text-sm disabled:opacity-40 transition-opacity"
        >
          {loading ? 'Computing...' : 'Compute Probability'}
        </button>
      </div>

      {result && (
        <div className="atlas-card">
          <div className="text-center mb-4">
            <div className="text-[10px] uppercase tracking-wider text-text-secondary mb-1">Fill Probability</div>
            <div className={`text-5xl font-mono font-bold ${
              (result.fill_probability_pct ?? 0) >= 60 ? 'text-bull' :
              (result.fill_probability_pct ?? 0) <= 40 ? 'text-bear' : 'text-text-primary'
            }`}>
              {result.fill_probability_pct != null ? `${result.fill_probability_pct}%` : '—'}
            </div>
            <div className="mt-1">
              <ConfidenceBadge confidence={result.confidence} n={result.sample_size} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm mb-4">
            <MetricSmall label="Median Fill Time" value={result.median_fill_time_minutes ? `${result.median_fill_time_minutes} min` : '—'} />
            <MetricSmall label="Avg MAE" value={result.avg_mae_pts ? `${result.avg_mae_pts} pts` : '—'} />
            <MetricSmall label="Fill by 10:30" value={result.fill_by_1030_pct != null ? `${result.fill_by_1030_pct}%` : '—'} />
            <MetricSmall label="Fill by 12:00" value={result.fill_by_1200_pct != null ? `${result.fill_by_1200_pct}%` : '—'} />
            <MetricSmall label="Edge Score" value={`${result.edge_score}/100`} color={result.edge_score > 60 ? 'text-bull' : result.edge_score > 30 ? 'text-gold' : 'text-bear'} />
            <MetricSmall label="Base Rate" value={result.base_rate_pct != null ? `${result.base_rate_pct}%` : '—'} />
          </div>

          <div className="text-[10px] text-text-secondary">
            <span className="uppercase tracking-wider">Filters applied: </span>
            {result.applied_filters.join(' · ')}
          </div>
        </div>
      )}
    </div>
  )
}

function MetricSmall({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div className="text-[9px] uppercase tracking-wider text-text-secondary">{label}</div>
      <div className={`font-mono font-semibold text-sm ${color || 'text-text-primary'}`}>{value}</div>
    </div>
  )
}
