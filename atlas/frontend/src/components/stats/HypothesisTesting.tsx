import { useEffect, useState } from 'react'
import { fetchHypothesisTests } from '../../lib/api'

interface HypTest {
  id: string
  claim: string
  result: Record<string, unknown>
  verdict: 'confirmed' | 'rejected' | 'insufficient' | 'no_data' | 'error'
  badge: string
}

const VERDICT_STYLES: Record<string, string> = {
  confirmed: 'border-bull/30 bg-bull/10',
  rejected: 'border-bear/30 bg-bear/10',
  insufficient: 'border-border bg-surface',
  no_data: 'border-border bg-surface',
  error: 'border-border bg-surface',
}

const VERDICT_LABEL: Record<string, string> = {
  confirmed: 'CONFIRMED',
  rejected: 'REJECTED',
  insufficient: 'INSUFFICIENT DATA',
  no_data: 'NO DATA',
  error: 'ERROR',
}

const VERDICT_COLOR: Record<string, string> = {
  confirmed: 'text-bull',
  rejected: 'text-bear',
  insufficient: 'text-text-secondary',
  no_data: 'text-text-secondary',
  error: 'text-text-secondary',
}

export function HypothesisTesting() {
  const [tests, setTests] = useState<HypTest[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchHypothesisTests()
      .then((r) => setTests(r.data.tests ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="space-y-3">{[...Array(5)].map((_, i) => <div key={i} className="atlas-card h-20 animate-pulse" />)}</div>

  if (tests.length === 0) {
    return (
      <div className="atlas-card text-center py-8 text-text-secondary text-sm">
        Hypothesis tests require historical data. Run the initial data population first.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="text-[11px] uppercase tracking-wider text-text-secondary mb-2">
        Empirical Tests of Dalton/Steidlmayer Claims
      </div>
      {tests.map((t) => (
        <div key={t.id} className={`rounded-2xl border p-4 ${VERDICT_STYLES[t.verdict]}`}>
          <div className="flex items-start justify-between gap-3 mb-2">
            <div>
              <span className="text-[10px] font-mono text-text-secondary">{t.id}</span>
              <p className="text-sm text-text-primary mt-0.5 leading-snug">{t.claim}</p>
            </div>
            <div className="flex-shrink-0 text-center">
              <div className="text-xl">{t.badge}</div>
              <div className={`text-[9px] uppercase tracking-wider font-semibold ${VERDICT_COLOR[t.verdict]}`}>
                {VERDICT_LABEL[t.verdict]}
              </div>
            </div>
          </div>
          <ResultDetails id={t.id} result={t.result} verdict={t.verdict} />
        </div>
      ))}
      <p className="text-[10px] text-text-secondary text-center pt-2">
        Tests run on available historical ES data. P-values computed via binomial test where applicable.
      </p>
    </div>
  )
}

function ResultDetails({ id, result, verdict }: { id: string; result: Record<string, unknown>; verdict: string }) {
  if (verdict === 'insufficient' || verdict === 'no_data') {
    return <p className="text-xs text-text-secondary">N={String(result.n ?? '—')} — more data needed for statistical significance</p>
  }

  const items: { label: string; value: string }[] = []

  if (id === 'H1' && result.rate != null) {
    items.push({ label: 'Actual rate', value: `${result.rate}%` })
    items.push({ label: 'Threshold', value: `${result.threshold}%` })
    items.push({ label: 'Sample', value: `N=${result.n}` })
  } else if (id === 'H2') {
    items.push({ label: 'Open-Drive trend rate', value: `${result.rate_drive}%` })
    items.push({ label: 'Open-Auction trend rate', value: `${result.rate_auction}%` })
    items.push({ label: 'N (Drive)', value: String(result.n_drive) })
    items.push({ label: 'N (Auction)', value: String(result.n_auction) })
  } else if (id === 'H3' && result.fill_rate != null) {
    items.push({ label: 'Actual fill rate', value: `${result.fill_rate}%` })
    items.push({ label: 'Threshold', value: `${result.threshold}%` })
    items.push({ label: 'Sample', value: `N=${result.n}` })
  } else if (id === 'H4') {
    items.push({ label: 'Narrow A avg range', value: `${result.narrow_avg_session_range} pts` })
    items.push({ label: 'Normal A avg range', value: `${result.normal_avg_session_range} pts` })
    items.push({ label: 'Ratio', value: String(result.ratio) })
  } else if (id === 'H5' && result.held_rate != null) {
    items.push({ label: 'A High held all day', value: `${result.held_rate}%` })
    items.push({ label: 'Threshold', value: `<${result.threshold}%` })
    items.push({ label: 'Sample', value: `N=${result.n}` })
  }

  if (items.length === 0) return null

  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5">
          <span className="text-[10px] text-text-secondary">{item.label}:</span>
          <span className="text-[11px] font-mono text-text-primary">{item.value}</span>
        </div>
      ))}
    </div>
  )
}
