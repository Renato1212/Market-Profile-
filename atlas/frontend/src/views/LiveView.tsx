import { APeriodTracker } from '../components/live/APeriodTracker'
import { KeyLevelsLadder } from '../components/live/KeyLevelsLadder'
import { AlertsFeed } from '../components/live/AlertsFeed'
import { AtlasBriefing } from '../components/ai/AtlasBriefing'
import { QuickStatsStrip } from '../components/live/QuickStatsStrip'
import { ErrorBoundary } from '../components/ui/ErrorBoundary'

export function LiveView() {
  return (
    <div className="space-y-4 pb-4">
      <ErrorBoundary compact fallbackTitle="Quick stats unavailable">
        <QuickStatsStrip />
      </ErrorBoundary>
      <ErrorBoundary compact fallbackTitle="AI briefing unavailable">
        <AtlasBriefing />
      </ErrorBoundary>
      <ErrorBoundary compact fallbackTitle="A Period tracker unavailable">
        <APeriodTracker />
      </ErrorBoundary>
      <ErrorBoundary compact fallbackTitle="Key levels unavailable">
        <KeyLevelsLadder />
      </ErrorBoundary>
      <ErrorBoundary compact fallbackTitle="Alerts feed unavailable">
        <AlertsFeed />
      </ErrorBoundary>
    </div>
  )
}
