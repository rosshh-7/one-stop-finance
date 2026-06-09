export type Direction = 'bullish' | 'bearish' | 'neutral'

export interface PredictionSignal {
  name: string
  raw_value: number
  display_value: string
  direction: Direction
  weight: number
}

export interface OptionsSnapshot {
  expiry: string
  put_call_ratio: number
  max_pain: number
  total_call_oi: number
  total_put_oi: number
  avg_call_iv: number
  avg_put_iv: number
  net_gex: number
}

export interface PricePrediction {
  symbol: string
  current_price: number
  direction: Direction
  confidence: number
  bull_score: number
  bear_score: number
  support: number | null
  resistance: number | null
  max_pain: number | null
  options: OptionsSnapshot | null
  signals: PredictionSignal[]
  horizon: string
  cached_at: string
}
