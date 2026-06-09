import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

export interface OptionContract {
  strike: number
  bid: number
  ask: number
  last: number
  volume: number
  open_interest: number
  implied_volatility: number
  delta: number
  in_the_money: boolean
}

export interface OptionsChain {
  symbol: string
  expiry: string
  expiries: string[]
  underlying_price: number
  max_pain: number
  put_call_ratio: number
  total_contracts: number
  calls: OptionContract[]
  puts: OptionContract[]
}

export interface StockScore {
  symbol: string
  score: number
  signal: string
  put_call_ratio: number
  max_pain: number
  underlying_price: number
  max_pain_pct: number
  call_volume: number
  put_volume: number
}

export interface ScannerResult {
  bullish: StockScore[]
  bearish: StockScore[]
  scanned_at: string
}

export function useOptionsScanner() {
  return useQuery<ScannerResult>({
    queryKey: ['options', 'scanner'],
    queryFn: () => apiClient.get('/options/scanner').then((r) => r.data.data),
    staleTime: 10 * 60_000, // 10 min — matches backend 15-min cache
    retry: 1,
  })
}

export function useOptionsChain(symbol: string, expiry?: string) {
  return useQuery<OptionsChain>({
    queryKey: ['options', 'chain', symbol, expiry ?? 'nearest'],
    queryFn: () =>
      apiClient
        .get(`/options/${symbol}`, { params: expiry ? { expiry } : {} })
        .then((r) => r.data.data),
    enabled: symbol.length > 0,
    staleTime: 60_000,
    retry: 1,
  })
}
