// ============================================================
// ATLAS TypeScript Type Definitions
// ============================================================

export type GexRegime = 'long' | 'short' | 'neutral'
export type GapDirection = 'up' | 'down' | 'none'
export type Confidence = 'high' | 'medium' | 'low' | 'insufficient'
export type DayType = 'trend_up' | 'trend_down' | 'normal_up' | 'normal_down' | 'neutral' | 'double_distribution' | 'trend_reversal' | 'unknown'
export type APeriodType = 'open_drive' | 'open_test_drive' | 'open_auction' | 'open_rejection_reverse' | 'open_gap' | 'narrow_a_period' | 'volatile_open'

export interface GapStats {
  gap_size_pts: number | null
  gap_size_pct: number | null
  gap_direction: GapDirection
  filled_same_session: boolean | null
  fill_time_minutes: number | null
  mae_before_fill_pts: number | null
  partial_fill_25pct: boolean | null
  partial_fill_50pct: boolean | null
  partial_fill_75pct: boolean | null
  gap_context: string | null
}

export interface FillRateStats {
  n: number
  fill_rate_pct: number | null
  confidence: Confidence
  avg_fill_time: number | null
  median_fill_time: number | null
  avg_mae: number | null
  fill_by_1030_pct: number | null
  fill_by_1200_pct: number | null
  fill_by_1400_pct: number | null
  no_fill_pct: number | null
}

export interface GapTableARow {
  context: string
  context_label: string
  all: FillRateStats
  gap_up: FillRateStats
  gap_down: FillRateStats
}

export interface GapTableBRow extends FillRateStats {
  size: string
  size_label: string
  direction: 'up' | 'down'
}

export interface CumulativeCurvePoint {
  minutes: number
  cumulative_fill_pct: number
}

export interface GapCalculatorResult {
  fill_probability_pct: number | null
  sample_size: number
  confidence: Confidence
  median_fill_time_minutes: number | null
  avg_mae_pts: number | null
  edge_score: number
  applied_filters: string[]
  base_rate_pct: number | null
  fill_by_1030_pct: number | null
  fill_by_1200_pct: number | null
  fill_by_1400_pct: number | null
}

export interface APeriodData {
  a_open: number
  a_high: number
  a_low: number
  a_close: number
  a_range: number
  a_volume: number
  a_close_position: number
  a_body_vs_range: number
  a_direction: 'bullish' | 'bearish' | 'neutral'
  a_type: APeriodType | null
  a_high_held_eod: boolean | null
  a_low_held_eod: boolean | null
  a_extension_direction: 'high' | 'low' | 'both' | 'neither'
  gap_filled_in_a_period: boolean | null
  ib_high?: number
  ib_low?: number
  ib_range?: number
}

export interface DayTypePrediction {
  probabilities: Record<string, number>
  top_prediction: DayType | null
  top_probability_pct: number
  confidence: Confidence
  bars_used: number
  a_close_position: number
  a_range: number
}

export interface GEXStrike {
  strike: number
  call_gex: number
  put_gex: number
  net_gex: number
  call_oi: number
  put_oi: number
  call_gamma: number
  put_gamma: number
  total_oi: number
}

export interface GEXRegimeDetail {
  name: GexRegime
  label: string
  description: string
  volatility_bias: string
  trading_style: string
  es_behavior: string
  color: string
}

export interface GEXDashboard {
  net_gex: number
  total_call_gex: number
  total_put_gex: number
  call_wall_spy: number | null
  put_wall_spy: number | null
  zero_gamma_spy: number | null
  call_wall_es: number | null
  put_wall_es: number | null
  zero_gamma_es: number | null
  regime: GexRegime
  regime_detail: GEXRegimeDetail
  strikes: GEXStrike[]
  unusual_activity: UnusualActivity[]
  spot_price: number
  es_spy_multiplier: number
  computed_at: string
}

export interface UnusualActivity {
  type: 'call' | 'put'
  strike: number
  expiration: string
  volume: number
  oi: number
  vol_oi_ratio: number
  premium: number
  institutional: boolean
}

export interface VIXTermStructure {
  vix: { current: number; prior_close: number; change: number; change_pct: number }
  vix9d: { current: number; prior_close: number; change: number; change_pct: number }
  vix3m: { current: number; prior_close: number; change: number; change_pct: number }
  vvix: { current: number; prior_close: number; change: number; change_pct: number }
  term_structure: {
    vix9d_vix_ratio: number
    vix_vix3m_ratio: number
    contango: boolean
    backwardation: boolean
    stress_flag: boolean
  }
}

export interface MarketSnapshot {
  es: { price: number; change: number; change_pct: number }
  vix: VIXTermStructure
  crypto: Record<string, { overnight_open: number; overnight_last: number; change_pct: number; risk_signal: string }>
  dxy: { current: number; change: number; change_pct: number }
  gex_regime: GexRegime | null
  gex_net: number | null
  timestamp: string
}

export interface KeyLevels {
  prior_close: number | null
  pdh: number | null
  pdl: number | null
  vah: number | null
  val: number | null
  poc: number | null
  call_wall_es: number | null
  put_wall_es: number | null
  zero_gamma_es: number | null
  on_high: number | null
  on_low: number | null
}

export interface Alert {
  id: string
  type: 'level_approach' | 'regime_shift' | 'a_period_complete' | 'gap_update' | 'macro_spike' | 'event_warning'
  content: string
  severity: 'info' | 'warning' | 'critical'
  timestamp: string
  dismissed: boolean
}

export interface LiveAPeriodState {
  date: string
  current_time_et: string
  in_a_period: boolean
  a_period_complete: boolean
  bars_count: number
  a_period: APeriodData | null
  day_type_prediction: DayTypePrediction | null
  prior_close: number | null
  pdh: number | null
  pdl: number | null
  bars: Array<{ bar_index: number; open: number; high: number; low: number; close: number; volume: number; time_et: string }>
}
