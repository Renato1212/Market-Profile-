import { Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import { Home, BarChart2, Zap, Bot, Database } from 'lucide-react'
import { clsx } from 'clsx'
import { LiveView } from './views/LiveView'
import { StatsView } from './views/StatsView'
import { FlowView } from './views/FlowView'
import { AtlasView } from './views/AtlasView'
import { DataView } from './views/DataView'
import { LandingPage } from './views/LandingPage'
import { ESPriceHeader } from './components/live/ESPriceHeader'
import { ComplianceFooter } from './components/ui/ComplianceFooter'
import { ErrorBoundary } from './components/ui/ErrorBoundary'

const NAV_ITEMS = [
  { to: '/live', icon: Home, label: 'Live' },
  { to: '/stats', icon: BarChart2, label: 'Stats' },
  { to: '/flow', icon: Zap, label: 'Flow' },
  { to: '/atlas', icon: Bot, label: 'Atlas' },
  { to: '/data', icon: Database, label: 'Data' },
]

function AppShell() {
  return (
    <div className="flex flex-col min-h-screen bg-bg">
      <ErrorBoundary compact fallbackTitle="Header unavailable">
        <ESPriceHeader />
      </ErrorBoundary>

      <main className="flex-1 overflow-y-auto px-4 pt-4 pb-20 max-w-2xl mx-auto w-full">
        <Routes>
          <Route path="/live" element={<ErrorBoundary><LiveView /></ErrorBoundary>} />
          <Route path="/stats" element={<ErrorBoundary><StatsView /></ErrorBoundary>} />
          <Route path="/flow" element={<ErrorBoundary><FlowView /></ErrorBoundary>} />
          <Route path="/atlas" element={<ErrorBoundary><AtlasView /></ErrorBoundary>} />
          <Route path="/data" element={<ErrorBoundary><DataView /></ErrorBoundary>} />
          <Route path="*" element={<Navigate to="/live" replace />} />
        </Routes>
        <ComplianceFooter />
      </main>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-surface border-t border-border safe-bottom z-50">
        <div className="flex max-w-2xl mx-auto">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex-1 flex flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium uppercase tracking-wider transition-colors',
                  isActive ? 'text-blue' : 'text-text-secondary hover:text-text-primary'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={18} strokeWidth={isActive ? 2.5 : 1.75} />
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}

export default function App() {
  const location = useLocation()
  const isLanding = location.pathname === '/'

  if (isLanding) return <LandingPage />

  return (
    <ErrorBoundary>
      <AppShell />
    </ErrorBoundary>
  )
}
