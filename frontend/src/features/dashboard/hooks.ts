import { useQuery } from '@tanstack/react-query'
import { apiClient, type ApiResponse } from '@/lib/api-client'

export interface ThemeScore {
  name: string
  slug: string
  benchmark_etf: string
  score: number
  level: 'alert' | 'watch' | 'quiet'
  unique_companies_buying: number
  total_value_accumulated: number
  primary_signal: string
  scored_at: string
}

export interface InsiderHighlight {
  symbol: string
  issuer_name: string
  insider_name: string
  insider_title: string
  transaction_type: 'buy' | 'sell' | 'exercise'
  total_value: number
  signal_score: number
  transaction_date: string
  sec_filing_url: string
}

export function useThemeIntelligence() {
  return useQuery({
    queryKey: ['public', 'theme-intelligence'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<{ themes: ThemeScore[] }>>('/public/theme-intelligence')
      return res.data.data.themes
    },
    staleTime: 14 * 60_000,
    refetchInterval: 15 * 60_000,
  })
}

export function useInsiderHighlights() {
  return useQuery({
    queryKey: ['public', 'insider-highlights'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<{ highlights: InsiderHighlight[] }>>('/public/insider-highlights')
      return res.data.data.highlights
    },
    staleTime: 4 * 60 * 60_000,
    refetchInterval: 4 * 60 * 60_000,
  })
}
