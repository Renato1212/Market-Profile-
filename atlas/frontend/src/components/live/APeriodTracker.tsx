import { useEffect, useState } from 'react'
import { ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { Clock } from 'lucide-react'
import { clsx } from 'clsx'
import { Card, Metric, MetricGrid } from '../ui/Card'
import { fetchLiveAPeriod } from '../../lib/api'
import type { LiveAPeriodState, APeriodType } from '../../types'

const A_TYPE_LABELS: Record<APeriodType, string> = {
  open_drive: 'OPEN DRIVE',
  open_test_drive: 'OPEN TEST-DRIVE',
  open_auction: 'OPEN AUCTION',
  open_rejection_reverse: 'REJECTION-REVERSE',
  open_gap: 'OPEN GAP',
  narrow_a_period: 'NARROW A PERIOD',
  volatile_open: 'VOLATILE OPEN',
}

const A_TYPE_COLORS: Record<APeriodType, string> = {
  open_drive: '#10D982',
  open_test_drive: '#4D9FFF',
  open_auction: '#6B7B95',
  open_rejection_reverse: '#FF3855',
  open_gap: '#FFB800',
  narrow_a_period: '#A855F7',
  volatile_open: '#FF8C42',
}

export function APeriodTracker() {
  const [data, setData] = useState<LiveAPeriodState | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetchLiveAPeriod()
        setData(res.data)
      } catch {} finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="atlas-card animate-pulse h-48" />

  const ap = data?.a_period
  const pred = data?.day_type_prediction
  const bars = data?.bars ?? []

  const chartData = bars.map((b) => ({
    time: b.time_et,
    open: b.open,
    high: b.high,
    low: b.low,
    close: b.close,
    bullish: b.close >= b.open ? b.close - b.open : 0,
    bearish: b.close < b.open ? b.open - b.close : 0,
  }))

  const aType = ap?.a_type as APeriodType | null
  const typeColor = aType ? A_TYPE_COLORS[aType] : '#6B7B95'
  const typeLabel = aType ? A_TYPE_LABELS[aType] : 'Computing...'

  return (
    <Card title="A PERIOD (09:30–10:00 ET)" titleRight={
      <div className="flex items-center gap-1.5">
        {data?.in_a_period && (
          <span className="text-xs font-mono text-bull live-indicator">● LIVE</span>
        )}
        {data?.a_period_complete && (
          <span className="text-xs font-mono text-gold">● COMPLETE</span>
        )}
      </div>
    }>
      {/* A Period Type Badge */}
      {aType && (
        <div className="mb-3 inline-flex items-center gap-2 px-3 py-1 rounded-lg border"
          style={{ borderColor: typeColor, color: typeColor, background: `${typeColor}18` }}>
          <span className="text-sm font-mono font-semibold">{typeLabel}</span>
        </div>
      )}

      {/* Mini Candlestick Chart */}
      {chartData.length > 0 && (
        <div className="h-28 mb-3">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
              <XAxis dataKey="time" tick={{ fill: '#6B7B95', fontSize: 10 }} tickLine={false} />
              <YAxis domain={['dataMin - 1', 'dataMax + 1']} tick={{ fill: '#6B7B95', fontSize: 10 }} width={50} tickLine={false} tickFormatter={(v) => v.toFixed(0)} />
              <Tooltip
                contentStyle={{ background: '#0D1424', border: '1px solid #1E2A3F', borderRadius: 8 }}
                labelStyle={{ color: '#6B7B95', fontSize: 11 }}
                itemStyle={{ color: '#E8EDF7', fontSize: 12, fontFamily: 'JetBrains Mono' }}
              />
              {data?.prior_close && (
                <ReferenceLine y={data.prior_close} stroke="#FFB800" strokeDasharray="3 3" strokeWidth={1} />
              )}
              {ap?.a_high && (
                <ReferenceLine y={ap.a_high} stroke="#10D982" strokeDasharray="2 2" strokeWidth={1} />
              )}
              {ap?.a_low && (
                <ReferenceLine y={ap.a_low} stroke="#FF3855" strokeDasharray="2 2" strokeWidth={1} />
              )}
              <Bar dataKey="bullish" fill="#10D982" stackId="candle" opacity={0.9} radius={1} />
              <Bar dataKey="bearish" fill="#FF3855" stackId="candle" opacity={0.9} radius={1} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* A Period Metrics */}
      {ap && (
        <MetricGrid cols={3}>
          <Metric label="A Range" value={ap.a_range != null ? ap.a_range.toFixed(2) : '—'} sub="pts" />
          <Metric
            label="Close Pos"
            value={ap.a_close_position != null ? `${ap.a_close_position.toFixed(1)}%` : '—'}
            color={
              ap.a_close_position != null
                ? ap.a_close_position > 66 ? '#10D982' : ap.a_close_position < 34 ? '#FF3855' : '#6B7B95'
                : '#6B7B95'
            }
          />
          <Metric
            label="Body/Range"
            value={ap.a_body_vs_range != null ? `${(ap.a_body_vs_range * 100).toFixed(0)}%` : '—'}
          />
        </MetricGrid>
      )}

      {/* Day Type Prediction */}
      {pred && (
        <div className="mt-3 pt-3 border-t border-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase tracking-wider text-text-secondary">Day Type Probability</span>
            <span className="text-xs font-mono text-text-secondary">N={pred.bars_used} bars</span>
          </div>
          <div className="space-y-1.5">
            {Object.entries(pred.probabilities ?? {})
              .sort(([, a], [, b]) => b - a)
              .map(([type, pct]) => (
                <DayTypeBar key={type} type={type} pct={pct} isTop={type === pred.top_prediction} />
              ))}
          </div>
        </div>
      )}
    </Card>
  )
}

function DayTypeBar({ type, pct, isTop }: { type: string; pct: number; isTop: boolean }) {
  const colors: Record<string, string> = {
    trend_up: '#10D982',
    trend_down: '#FF3855',
    normal_up: '#4D9FFF',
    normal_down: '#FF8C42',
    neutral: '#6B7B95',
  }
  const labels: Record<string, string> = {
    trend_up: 'Trend Up',
    trend_down: 'Trend Down',
    normal_up: 'Normal Up',
    normal_down: 'Normal Down',
    neutral: 'Neutral',
  }
  const color = colors[type] || '#6B7B95'

  return (
    <div className={clsx('flex items-center gap-2', isTop && 'font-semibold')}>
      <span className="text-[11px] w-20 text-text-secondary">{labels[type] || type}</span>
      <div className="flex-1 bg-bg rounded-full h-1.5 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="text-[11px] font-mono w-9 text-right" style={{ color: isTop ? color : '#6B7B95' }}>
        {pct.toFixed(0)}%
      </span>
    </div>
  )
}
