import { useState } from 'react'
import { GapTables } from '../components/stats/GapTables'
import { GapCalculator } from '../components/stats/GapCalculator'
import { HypothesisTesting } from '../components/stats/HypothesisTesting'

const TABS = [
  { id: 'gap', label: 'Gap Fill' },
  { id: 'calc', label: 'Calculator' },
  { id: 'hypothesis', label: 'Hypothesis Tests' },
]

export function StatsView() {
  const [tab, setTab] = useState('gap')
  return (
    <div className="pb-4">
      <div className="flex gap-1 mb-4 bg-surface rounded-xl p-1 border border-border">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              tab === t.id ? 'bg-blue text-bg' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'gap' && <GapTables />}
      {tab === 'calc' && <GapCalculator />}
      {tab === 'hypothesis' && <HypothesisTesting />}
    </div>
  )
}
