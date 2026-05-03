import { APeriodTracker } from '../components/live/APeriodTracker'
import { KeyLevelsLadder } from '../components/live/KeyLevelsLadder'
import { AlertsFeed } from '../components/live/AlertsFeed'
import { AtlasBriefing } from '../components/ai/AtlasBriefing'
import { QuickStatsStrip } from '../components/live/QuickStatsStrip'

export function LiveView() {
  return (
    <div className="space-y-4 pb-4">
      <QuickStatsStrip />
      <AtlasBriefing />
      <APeriodTracker />
      <KeyLevelsLadder />
      <AlertsFeed />
    </div>
  )
}
