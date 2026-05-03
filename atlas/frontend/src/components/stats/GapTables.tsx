import { useEffect, useState } from 'react'
import { fetchGapTables } from '../../lib/api'
import { ConfidenceBadge } from '../ui/Badge'
import type { GapTableARow, GapTableBRow, CumulativeCurvePoint } from '../../types'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

export function GapTables() {
  const [tables, setTables] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'A' | 'B' | 'C'>('A')

  useEffect(() => {
    fetchGapTables(10).then((r) => { setTables(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="atlas-card h-64 animate-pulse" />
  if (!tables) return <div className="atlas-card text-center py-8 text-text-secondary">Gap data loading...</div>

  return (
    <div>
      <div className="flex gap-2 mb-4">
        {(['A', 'B', 'C'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-mono transition-colors ${
              activeTab === t
                ? 'bg-blue text-bg font-semibold'
                : 'bg-surface text-text-secondary border border-border hover:border-blue'
            }`}
          >
            Table {t}
          </button>
        ))}
        <div className="ml-auto text-xs text-text-secondary self-center">
          {tables.total_sessions} sessions · {tables.date_range?.start} – {tables.date_range?.end}
        </div>
      </div>

      {activeTab === 'A' && <TableA rows={tables.table_a} />}
      {activeTab === 'B' && <TableB rows={tables.table_b} />}
      {activeTab === 'C' && <TableC data={tables.table_c} />}
    </div>
  )
}

function TableA({ rows }: { rows: GapTableARow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-2 px-3 text-[10px] uppercase tracking-wider text-text-secondary font-medium">Opening Location</th>
            {['All', 'Gap Up', 'Gap Down'].map((h) => (
              <th key={h} colSpan={4} className="text-center py-2 px-2 text-[10px] uppercase tracking-wider text-text-secondary font-medium border-l border-border">
                {h}
              </th>
            ))}
          </tr>
          <tr className="border-b border-border">
            <th />
            {[...Array(3)].flatMap((_, i) => (
              ['N', 'Fill%', 'Avg Fill', 'Conf'].map((h) => (
                <th key={`${i}-${h}`} className={`py-1.5 px-2 text-[9px] uppercase tracking-wider text-text-secondary font-medium text-right ${h === 'N' ? 'border-l border-border' : ''}`}>{h}</th>
              ))
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.context} className="border-b border-border/50 hover:bg-surface/50">
              <td className="py-2 px-3 text-xs text-text-secondary font-mono">{row.context_label}</td>
              {[row.all, row.gap_up, row.gap_down].flatMap((stats, i) => [
                <td key={`${i}-n`} className="py-2 px-2 text-right font-mono text-xs text-text-secondary border-l border-border">{stats.n || '—'}</td>,
                <td key={`${i}-fill`} className={`py-2 px-2 text-right font-mono text-sm font-semibold ${getColorForFillRate(stats.fill_rate_pct)}`}>
                  {stats.fill_rate_pct != null ? `${stats.fill_rate_pct}%` : '—'}
                </td>,
                <td key={`${i}-time`} className="py-2 px-2 text-right font-mono text-xs text-text-secondary">
                  {stats.avg_fill_time ? `${stats.avg_fill_time}m` : '—'}
                </td>,
                <td key={`${i}-conf`} className="py-2 px-2 text-right">
                  {stats.n >= 10 ? <ConfidenceBadge confidence={stats.confidence} /> : <span className="text-[9px] text-text-secondary">⚫ LOW</span>}
                </td>,
              ])}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TableB({ rows }: { rows: GapTableBRow[] }) {
  const upRows = rows.filter((r) => r.direction === 'up')
  const downRows = rows.filter((r) => r.direction === 'down')

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <SizeTable title="Gap Up" rows={upRows} color="#10D982" />
      <SizeTable title="Gap Down" rows={downRows} color="#FF3855" />
    </div>
  )
}

function SizeTable({ title, rows, color }: { title: string; rows: GapTableBRow[]; color: string }) {
  return (
    <div className="atlas-card">
      <div className="text-[11px] uppercase tracking-wider mb-3" style={{ color }}>{title}</div>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border">
            {['Size', 'N', 'Fill%', 'Med Fill', 'Avg MAE'].map((h) => (
              <th key={h} className="py-1.5 text-left text-[9px] uppercase tracking-wider text-text-secondary pr-3">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.size} className="border-b border-border/40">
              <td className="py-2 pr-3 text-text-secondary font-mono">{row.size}</td>
              <td className="py-2 pr-3 font-mono text-text-secondary">{row.n || '—'}</td>
              <td className={`py-2 pr-3 font-mono font-semibold ${getColorForFillRate(row.fill_rate_pct)}`}>
                {row.fill_rate_pct != null ? `${row.fill_rate_pct}%` : '—'}
              </td>
              <td className="py-2 pr-3 font-mono text-text-secondary">{row.median_fill_time ? `${row.median_fill_time}m` : '—'}</td>
              <td className="py-2 font-mono text-text-secondary">{row.avg_mae ? `${row.avg_mae}` : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TableC({ data }: { data: { curve: CumulativeCurvePoint[]; half_life_minutes: number | null; curve_up: CumulativeCurvePoint[]; curve_down: CumulativeCurvePoint[] } }) {
  const chartData = data.curve?.map((pt, i) => ({
    minutes: pt.minutes,
    all: pt.cumulative_fill_pct,
    up: data.curve_up?.[i]?.cumulative_fill_pct,
    down: data.curve_down?.[i]?.cumulative_fill_pct,
  })) ?? []

  return (
    <div className="atlas-card">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[11px] uppercase tracking-wider text-text-secondary">Cumulative Fill Probability</span>
        {data.half_life_minutes && (
          <span className="text-xs font-mono text-gold">
            50% half-life: {data.half_life_minutes}min
          </span>
        )}
      </div>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 20, left: 0 }}>
            <XAxis
              dataKey="minutes"
              tick={{ fill: '#6B7B95', fontSize: 10 }}
              tickLine={false}
              label={{ value: 'Minutes from 09:30', position: 'insideBottom', fill: '#6B7B95', fontSize: 10, offset: -10 }}
              tickFormatter={(v) => v === 60 ? '10:30' : v === 150 ? '12:00' : v === 270 ? '14:00' : `${v}m`}
            />
            <YAxis tick={{ fill: '#6B7B95', fontSize: 10 }} tickLine={false} tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
            <Tooltip
              contentStyle={{ background: '#0D1424', border: '1px solid #1E2A3F', borderRadius: 8 }}
              formatter={(val: number, name: string) => [`${val?.toFixed(1)}%`, name]}
            />
            <ReferenceLine y={50} stroke="#FFB800" strokeDasharray="3 3" strokeWidth={1} />
            <Line type="monotone" dataKey="all" stroke="#4D9FFF" strokeWidth={2} dot={false} name="All Gaps" />
            <Line type="monotone" dataKey="up" stroke="#10D982" strokeWidth={1.5} dot={false} name="Gap Up" strokeDasharray="4 2" />
            <Line type="monotone" dataKey="down" stroke="#FF3855" strokeWidth={1.5} dot={false} name="Gap Down" strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 flex gap-4 justify-center">
        <LegendLine color="#4D9FFF" label="All Gaps" />
        <LegendLine color="#10D982" label="Gap Up" dash />
        <LegendLine color="#FF3855" label="Gap Down" dash />
      </div>
    </div>
  )
}

function LegendLine({ color, label, dash }: { color: string; label: string; dash?: boolean }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-6 border-t-2" style={{ borderColor: color, borderStyle: dash ? 'dashed' : 'solid' }} />
      <span className="text-[10px] text-text-secondary">{label}</span>
    </div>
  )
}

function getColorForFillRate(pct: number | null): string {
  if (pct === null) return 'text-text-secondary'
  if (pct >= 65) return 'text-bull'
  if (pct <= 35) return 'text-bear'
  return 'text-text-primary'
}
