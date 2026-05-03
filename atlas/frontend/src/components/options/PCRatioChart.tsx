import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { fetchPCRatio } from '../../lib/api'
import { Card } from '../ui/Card'

export function PCRatioChart() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchPCRatio()
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="atlas-card h-48 animate-pulse" />
  if (!data) return <div className="atlas-card text-center py-8 text-text-secondary">P/C data unavailable</div>

  const signalColor = data.signal?.includes('fear') ? '#10D982' :
    data.signal?.includes('complacency') ? '#FF3855' : '#6B7B95'

  const chartPoints = (data.history ?? []).map((h: any) => ({
    date: String(h.date).slice(5),
    ratio: typeof h.total_pc_ratio === 'number' ? h.total_pc_ratio : null,
  }))

  return (
    <div className="space-y-4">
      <Card title="CBOE PUT/CALL RATIO">
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div>
            <div className="text-[10px] text-text-secondary uppercase mb-0.5">Latest</div>
            <div className="text-xl font-mono font-bold text-text-primary">{data.latest?.toFixed(3)}</div>
          </div>
          <div>
            <div className="text-[10px] text-text-secondary uppercase mb-0.5">10d MA</div>
            <div className="text-xl font-mono font-bold text-text-primary">{data.ma10?.toFixed(3)}</div>
          </div>
          <div>
            <div className="text-[10px] text-text-secondary uppercase mb-0.5">1Y Pctile</div>
            <div className="text-xl font-mono font-bold text-text-primary">{data.percentile_1y?.toFixed(0)}%</div>
          </div>
        </div>

        <div
          className="rounded-xl px-3 py-2 mb-4 text-sm"
          style={{ background: `${signalColor}15`, border: `1px solid ${signalColor}40`, color: signalColor }}
        >
          {data.interpretation}
        </div>

        {chartPoints.length > 0 && (
          <div className="h-32">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartPoints} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
                <XAxis dataKey="date" tick={{ fill: '#6B7B95', fontSize: 9 }} tickLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill: '#6B7B95', fontSize: 9 }} tickLine={false} domain={[0.5, 1.5]} />
                <Tooltip
                  contentStyle={{ background: '#0D1424', border: '1px solid #1E2A3F', borderRadius: 8 }}
                  formatter={(v: number) => [v?.toFixed(3), 'P/C Ratio']}
                />
                <ReferenceLine y={1.1} stroke="#10D982" strokeDasharray="3 3" label={{ value: 'Bearish Extreme', fill: '#10D982', fontSize: 9 }} />
                <ReferenceLine y={0.7} stroke="#FF3855" strokeDasharray="3 3" label={{ value: 'Bullish Extreme', fill: '#FF3855', fontSize: 9 }} />
                <Line type="monotone" dataKey="ratio" stroke="#4D9FFF" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="mt-3 text-[10px] text-text-secondary">
          Source: CBOE total P/C archive · Bearish extreme: {'>'}1.1 · Bullish extreme: {'<'}0.7
        </div>
      </Card>
    </div>
  )
}
