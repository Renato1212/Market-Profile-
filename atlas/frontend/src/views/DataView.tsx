import { useEffect, useState } from 'react'
import { Download } from 'lucide-react'
import { fetchDailyOHLCV } from '../lib/api'

export function DataView() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState('date')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    fetchDailyOHLCV('ES=F', 2)
      .then((r) => setData(r.data.data?.slice().reverse() ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const sorted = [...data].sort((a, b) => {
    const av = a[sortKey]
    const bv = b[sortKey]
    if (av === bv) return 0
    const cmp = av > bv ? 1 : -1
    return sortDir === 'asc' ? cmp : -cmp
  })

  const toggle = (key: string) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const exportCSV = () => {
    const headers = Object.keys(sorted[0] || {}).join(',')
    const rows = sorted.map(r => Object.values(r).join(',')).join('\n')
    const blob = new Blob([headers + '\n' + rows], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'atlas-es-data.csv'
    a.click()
  }

  return (
    <div className="pb-4">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[11px] uppercase tracking-wider text-text-secondary">ES Historical Sessions</span>
        <button
          onClick={exportCSV}
          className="flex items-center gap-1.5 text-xs text-blue hover:text-text-primary border border-border rounded-lg px-3 py-1.5 transition-colors"
        >
          <Download size={12} /> Export CSV
        </button>
      </div>

      {loading ? (
        <div className="atlas-card h-64 animate-pulse" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                {['date', 'open', 'high', 'low', 'close', 'volume'].map((col) => (
                  <th
                    key={col}
                    onClick={() => toggle(col)}
                    className="text-left py-2 px-3 text-[10px] uppercase tracking-wider text-text-secondary cursor-pointer hover:text-text-primary select-none"
                  >
                    {col} {sortKey === col ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.slice(0, 100).map((row, i) => (
                <tr key={i} className="border-b border-border/40 hover:bg-surface/50">
                  <td className="py-1.5 px-3 font-mono text-text-secondary">{row.date}</td>
                  <td className="py-1.5 px-3 font-mono">{row.open?.toFixed(2)}</td>
                  <td className="py-1.5 px-3 font-mono text-bull">{row.high?.toFixed(2)}</td>
                  <td className="py-1.5 px-3 font-mono text-bear">{row.low?.toFixed(2)}</td>
                  <td className={`py-1.5 px-3 font-mono font-semibold ${row.close > row.open ? 'text-bull' : 'text-bear'}`}>
                    {row.close?.toFixed(2)}
                  </td>
                  <td className="py-1.5 px-3 font-mono text-text-secondary">
                    {row.volume ? (row.volume / 1000).toFixed(0) + 'K' : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-[10px] text-text-secondary mt-2 px-3">Showing 100 of {sorted.length} sessions</p>
        </div>
      )}
    </div>
  )
}
