import { Lock } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Tier } from '../../lib/tiers'
import { DEFAULT_DEV_TIER, TIER_CONFIGS } from '../../lib/tiers'

interface TierGateProps {
  requiredTier: Tier
  children: React.ReactNode
  featureName?: string
}

const TIER_ORDER: Tier[] = ['free', 'pro', 'elite', 'institutional']

function tierLevel(t: Tier) {
  return TIER_ORDER.indexOf(t)
}

export function TierGate({ requiredTier, children, featureName }: TierGateProps) {
  const userTier = DEFAULT_DEV_TIER // Replace with auth store in production

  if (tierLevel(userTier) >= tierLevel(requiredTier)) {
    return <>{children}</>
  }

  return (
    <div className="atlas-card text-center py-10">
      <div className="w-12 h-12 rounded-2xl bg-surface border border-border flex items-center justify-center mx-auto mb-4">
        <Lock size={20} className="text-text-secondary" />
      </div>
      <h3 className="font-semibold text-text-primary mb-1">
        {featureName ?? 'This Feature'} requires {requiredTier.charAt(0).toUpperCase() + requiredTier.slice(1)}
      </h3>
      <p className="text-sm text-text-secondary mb-4">
        Upgrade to unlock {featureName ?? 'this feature'} and all {requiredTier} capabilities.
      </p>
      <Link
        to="/#pricing"
        className="inline-flex items-center gap-2 bg-blue text-bg text-sm font-semibold px-5 py-2.5 rounded-xl hover:bg-blue/90 transition-colors"
      >
        View Plans →
      </Link>
    </div>
  )
}
