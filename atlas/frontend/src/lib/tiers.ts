export type Tier = 'free' | 'pro' | 'elite' | 'institutional'

export interface TierConfig {
  gap_history_years: number
  ai_alerts_per_day: number
  chat_queries_per_day: number
  options_refresh_minutes: number
  export_enabled: boolean
  webhooks_enabled: boolean
  api_access: boolean
  full_gex: boolean
  full_a_period: boolean
  probability_calculator: boolean
}

export const TIER_CONFIGS: Record<Tier, TierConfig> = {
  free: {
    gap_history_years: 1,
    ai_alerts_per_day: 1,
    chat_queries_per_day: 3,
    options_refresh_minutes: 60,
    export_enabled: false,
    webhooks_enabled: false,
    api_access: false,
    full_gex: false,
    full_a_period: false,
    probability_calculator: false,
  },
  pro: {
    gap_history_years: 12,
    ai_alerts_per_day: 50,
    chat_queries_per_day: 50,
    options_refresh_minutes: 15,
    export_enabled: true,
    webhooks_enabled: false,
    api_access: false,
    full_gex: true,
    full_a_period: true,
    probability_calculator: true,
  },
  elite: {
    gap_history_years: 12,
    ai_alerts_per_day: 999,
    chat_queries_per_day: 999,
    options_refresh_minutes: 5,
    export_enabled: true,
    webhooks_enabled: true,
    api_access: true,
    full_gex: true,
    full_a_period: true,
    probability_calculator: true,
  },
  institutional: {
    gap_history_years: 12,
    ai_alerts_per_day: 9999,
    chat_queries_per_day: 9999,
    options_refresh_minutes: 1,
    export_enabled: true,
    webhooks_enabled: true,
    api_access: true,
    full_gex: true,
    full_a_period: true,
    probability_calculator: true,
  },
}

// In dev/demo mode, default to 'pro' so all features are accessible
export const DEFAULT_DEV_TIER: Tier = 'pro'

export function getTierConfig(tier: Tier): TierConfig {
  return TIER_CONFIGS[tier] ?? TIER_CONFIGS.free
}
