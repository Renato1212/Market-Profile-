import { useState } from 'react'
import { GEXDashboard } from '../components/options/GEXDashboard'
import { PCRatioChart } from '../components/options/PCRatioChart'
import { UnusualActivityTable } from '../components/options/UnusualActivityTable'
import { VIXTermStructureChart } from '../components/options/VIXTermStructureChart'

const TABS = [
  { id: 'gex', label: 'GEX' },
  { id: 'flow', label: 'Flow' },
  { id: 'iv', label: 'IV/Vol' },
  { id: 'pc', label: 'P/C Ratio' },
]

export function FlowView() {
  const [tab, setTab] = useState('gex')
  return (
    <div className="pb-4">
      <div className="flex gap-1 mb-4 bg-surface rounded-xl p-1 border border-border overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-shrink-0 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              tab === t.id ? 'bg-blue text-bg' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'gex' && <GEXDashboard />}
      {tab === 'flow' && <UnusualActivityTable />}
      {tab === 'iv' && <VIXTermStructureChart />}
      {tab === 'pc' && <PCRatioChart />}
    </div>
  )
}
