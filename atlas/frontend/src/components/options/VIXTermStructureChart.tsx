import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { fetchTermStructure } from '../../lib/api'
import type { VIXTermStructure } from '../../types'
import { Card } from '../ui/Card'

export function VIXTermStructureChart() {
  const [data, setData] = useState<VIXTermStructure | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTermStructure()
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))

    const interval = setInterval(() => {
      fetchTermStructure().then((r) => setData(r.data)).catch(() => {})
    }, 300000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="atlas-card h-48 animate-pulse" />
  if (!data) return <div className="atlas-card text-center py-8 text-text-secondary">VIX data unavailable</div>

  const ts = data.term_structure
  const chartData = [
    { name: 'VIX9D', value: data.vix9d?.current, change: data.vix9d?.change },
    { name: 'VIX', value: data.vix?.current, change: data.vix?.change },
    { name: 'VIX3M', value: data.vix3m?.current, change: data.vix3m?.change },
  ]

  const structureLabel = ts?.backwardation ? 'BACKWARDATION — Stress Event' : 'CONTANGO — Calm'
  const structureColor = ts?.backwardation ? '#FF3855' : '#10D982'

  return (
    <div className="space-y-4">
      <Card title="VIX TERM STRUCTURE">
        <div
          className="rounded-xl px-3 py-2 mb-4 text-sm font-mono font-semibold"
          style={{ background: `${structureColor}15`, border: `1px solid ${structureColor}40`, color: structureColor }}
        >
          {structureLabel}
        </div>

        <div className="h-36 mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
              <XAxis dataKey="name" tick={{ fill: '#6B7B95', fontSize: 11 }} tickLine={false} />
              <YAxis tick={{ fill: '#6B7B95', fontSize: 10 }} tickLine={false} domain={['auto', 'auto']} />
              <Tooltip
                contentStyle={{ background: '#0D1424', border: '1px solid #1E2A3F', borderRadius: 8 }}
                formatter={(v: number, _: string, props: any) => [
                  `${v?.toFixed(2)} (${props.payload.change > 0 ? '+' : ''}${props.payload.change?.toFixed(2)})`,
                  'Level'
                ]}
              />
              <Bar dataKey="value" radius={4}>
                {chartData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={i === 0 ? '#4D9FFF' : i === 1 ? '#FFB800' : '#A855F7'}
                    opacity={0.85}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          {ts && (
            <>
              <Ratio label="VIX9D / VIX" value={ts.vix9d_vix_ratio} warn={ts.vix9d_vix_ratio > 1.0} />
              <Ratio label="VIX / VIX3M" value={ts.vix_vix3m_ratio} warn={ts.vix_vix3m_ratio > 1.0} />
            </>
          )}
        </div>

        {ts?.stress_flag && (
          <div className="mt-3 rounded-lg bg-bear/10 border border-bear/30 px-3 py-2 text-xs text-bear">
            ⚠️ VIX9D {'>'} VIX3M — Short-term stress elevated above longer-dated fear
          </div>
        )}
      </Card>

      <Card title="VIX LEVELS">
        <div className="space-y-3">
          {[
            { label: 'VIX (30-day)', d: data.vix, color: '#FFB800' },
            { label: 'VIX9D (9-day)', d: data.vix9d, color: '#4D9FFF' },
            { label: 'VIX3M (93-day)', d: data.vix3m, color: '#A855F7' },
            { label: 'VVIX (vol of VIX)', d: data.vvix, color: '#FF8C42' },
          ].map(({ label, d, color }) => (
            <div key={label} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{ background: color }} />
                <span className="text-sm text-text-secondary">{label}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-xs font-mono ${d?.change > 0 ? 'text-bear' : 'text-bull'}`}>
                  {d?.change > 0 ? '+' : ''}{d?.change?.toFixed(2)}
                </span>
                <span className="font-mono font-semibold" style={{ color }}>
                  {d?.current?.toFixed(2)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

function Ratio({ label, value, warn }: { label: string; value: number | null; warn: boolean }) {
  return (
    <div>
      <div className="text-[10px] text-text-secondary uppercase mb-0.5">{label}</div>
      <div className={`font-mono font-semibold ${warn ? 'text-bear' : 'text-bull'}`}>
        {value?.toFixed(3) ?? '—'}
        <span className="text-[10px] ml-1">{warn ? '⚠' : '✓'}</span>
      </div>
    </div>
  )
}
