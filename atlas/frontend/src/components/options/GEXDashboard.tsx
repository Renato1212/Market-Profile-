import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts'
import { RegimeBadge } from '../ui/Badge'
import { Card, Metric, MetricGrid } from '../ui/Card'
import { fetchGEXDashboard } from '../../lib/api'
import type { GEXDashboard as GEXData } from '../../types'

export function GEXDashboard() {
  const [data, setData] = useState<GEXData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetchGEXDashboard()
        setData(res.data)
      } catch {} finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 900000) // Refresh every 15 min
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="space-y-4 animate-pulse"><div className="atlas-card h-32" /><div className="atlas-card h-48" /></div>
  if (!data) return <div className="atlas-card text-center py-8 text-text-secondary">GEX data unavailable</div>

  const regimeDetail = data.regime_detail ?? { color: '#6B7B95', description: '', volatility_bias: '—', trading_style: '—' }
  const chartData = data.strikes
    .filter((s) => Math.abs(s.strike - data.spot_price) / data.spot_price <= 0.05)
    .map((s) => ({
      strike: s.strike.toFixed(0),
      net_gex: s.net_gex / 1e8,
      call_gex: s.call_gex / 1e8,
      put_gex: s.put_gex / 1e8,
    }))

  return (
    <div className="space-y-4">
      {/* Regime Card */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <RegimeBadge regime={data.regime} size="lg" />
          <div className="text-right">
            <div className="text-[10px] text-text-secondary uppercase tracking-wider">Net GEX</div>
            <div className="text-xl font-mono font-bold" style={{ color: regimeDetail.color }}>
              {data.net_gex != null ? `${data.net_gex > 0 ? '+' : ''}${data.net_gex.toFixed(2)}B` : '—'}
            </div>
          </div>
        </div>
        <p className="text-sm text-text-secondary leading-relaxed mb-3">{regimeDetail.description}</p>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <div className="text-[10px] text-text-secondary uppercase mb-1">Volatility Bias</div>
            <div className="font-mono" style={{ color: regimeDetail.color }}>{regimeDetail.volatility_bias}</div>
          </div>
          <div>
            <div className="text-[10px] text-text-secondary uppercase mb-1">Trading Style</div>
            <div className="text-text-primary text-xs">{regimeDetail.trading_style}</div>
          </div>
        </div>
      </Card>

      {/* Key Levels */}
      <Card title="OPTIONS KEY LEVELS (ES EQUIVALENT)">
        <div className="space-y-3">
          <LevelRow label="Call Wall (Resistance)" value={data.call_wall_es} color="#FFB800" />
          <LevelRow label="Put Wall (Support)" value={data.put_wall_es} color="#00E5A0" />
          <LevelRow label="Zero Gamma Flip" value={data.zero_gamma_es} color="#FF8C42" />
          <div className="pt-2 border-t border-border text-[10px] text-text-secondary">
            Multiplier: ES/SPY = {data.es_spy_multiplier?.toFixed(4)} (live)
          </div>
        </div>
      </Card>

      {/* GEX Profile Chart */}
      <Card title="GAMMA EXPOSURE BY STRIKE">
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
              <XAxis dataKey="strike" tick={{ fill: '#6B7B95', fontSize: 9 }} tickLine={false}
                interval="preserveStartEnd" />
              <YAxis tick={{ fill: '#6B7B95', fontSize: 9 }} tickLine={false} tickFormatter={(v) => `${v.toFixed(0)}B`} />
              <Tooltip
                contentStyle={{ background: '#0D1424', border: '1px solid #1E2A3F', borderRadius: 8 }}
                labelStyle={{ color: '#6B7B95', fontSize: 11 }}
                itemStyle={{ fontFamily: 'JetBrains Mono', fontSize: 11 }}
                formatter={(val: number) => [`${val.toFixed(2)}B`, '']}
              />
              <ReferenceLine y={0} stroke="#1E2A3F" />
              <Bar dataKey="net_gex" name="Net GEX" radius={2}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.net_gex >= 0 ? '#10D982' : '#FF3855'} opacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Key Stats */}
      <Card>
        <MetricGrid cols={2}>
          <Metric label="Call GEX" value={data.total_call_gex != null ? `+${data.total_call_gex.toFixed(2)}B` : '—'} color="#10D982" />
          <Metric label="Put GEX" value={data.total_put_gex != null ? `${data.total_put_gex.toFixed(2)}B` : '—'} color="#FF3855" />
          <Metric label="Call Wall (SPY)" value={data.call_wall_spy?.toFixed(2)} />
          <Metric label="Put Wall (SPY)" value={data.put_wall_spy?.toFixed(2)} />
        </MetricGrid>
      </Card>
    </div>
  )
}

function LevelRow({ label, value, color }: { label: string; value: number | null; color: string }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 rounded-full" style={{ background: color }} />
        <span className="text-sm text-text-secondary">{label}</span>
      </div>
      <span className="font-mono font-semibold" style={{ color }}>
        {value ? value.toFixed(2) : '—'}
      </span>
    </div>
  )
}
