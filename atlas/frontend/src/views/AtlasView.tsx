import { AtlasBriefing, AtlasChat } from '../components/ai/AtlasBriefing'
import { AlertsFeed } from '../components/live/AlertsFeed'

export function AtlasView() {
  return (
    <div className="space-y-4 pb-4">
      <AtlasBriefing />
      <AtlasChat />
      <AlertsFeed />
    </div>
  )
}
