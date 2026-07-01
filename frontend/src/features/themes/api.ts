import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient, type ApiResponse } from '@/lib/api-client'

// ---------------------------------------------------------------------------
// Sync types (existing)
// ---------------------------------------------------------------------------
export type SyncSourceKey = 'fmp' | 'trends' | 'polygon' | 'etf' | 'etf_signals'

export interface SyncSource {
  source: SyncSourceKey
  label: string
  description: string
  status: 'idle' | 'running' | 'error'
  last_synced_at: string | null
  is_stale: boolean
  stale_after_hours: number
  error: string | null
}

export interface SyncStatusData { sources: SyncSource[] }
export interface SyncTriggerData { triggered: SyncSourceKey[]; skipped: SyncSourceKey[] }

// ---------------------------------------------------------------------------
// Theme types
// ---------------------------------------------------------------------------
export interface ThemeScore {
  score: number
  level: 'alert' | 'watch' | 'quiet'
  velocity: number | null
  lifecycle_stage: string | null
  unique_companies_buying: number
  unique_companies_selling: number
  total_value_accumulated: number
  csuite_count: number
  congress_signal: boolean
  sentiment_signal: boolean
  unusual_options_count: number
  contracts_count: number
  trend_velocity: number | null
  options_anomaly: number | null
  signal_breakdown: {
    buying_tickers: string[]
    selling_tickers: string[]
    total_usd: number
    large_buys_count: number
    congress_tickers: string[]
    contracts_count: number
    sentiment_score?: number | null
    etf_vol_ratio?: number | null
    etf_price_change_pct?: number | null
    etf_flow_score?: number | null
    etf_put_call_ratio?: number | null
    etf_otm_call_oi?: number | null
    etf_iv_percentile?: number | null
    etf_options_score?: number | null
    signals_fired?: number | null
    convergence_bonus?: number | null
    activist_stake_count?: number | null
    institutional_new_positions?: number | null
    short_high_and_buying?: boolean | null
    ai_ecosystem_count?: number | null
    ai_ecosystem_usd?: number | null
    macro_aligned?: boolean | null
    nih_grant_count?: number | null
  } | null
  scored_at: string | null
  // Synthesis (filled daily by Claude Sonnet for score > 45)
  thesis: string | null
  watch_for: string | null
  confidence: 'high' | 'medium' | 'low' | null
  synthesized_at: string | null
}

export interface Theme {
  id: string
  name: string
  slug: string
  description: string | null
  category: string | null
  benchmark_etf: string | null
  score: ThemeScore | null
  top_tickers: string[]
}

export interface ThemeTicker {
  symbol: string
  company_name: string | null
  market_cap_tier: string | null
}

export interface HistoryPoint {
  scored_at: string
  score: number
  velocity: number | null
  lifecycle_stage: string | null
}

export interface ThemeDetail extends Theme {
  tickers: ThemeTicker[]
  history: HistoryPoint[]
}

export interface InsiderSignal {
  symbol: string
  issuer_name: string | null
  insider_name: string
  insider_title: string | null
  transaction_type: 'buy' | 'sell'
  total_value: number | null
  is_congress: boolean
  filing_date: string
}

export interface ContractSignal {
  recipient_name: string | null
  symbol: string | null
  award_amount: number | null
  agency_name: string | null
  description: string | null
  award_date: string | null
  theme_id: string | null
}

// ---------------------------------------------------------------------------
// Sync hooks
// ---------------------------------------------------------------------------
export function useSyncStatus() {
  const { data, ...rest } = useQuery({
    queryKey: ['themes', 'sync', 'status'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<SyncStatusData>>('/themes/sync/status')
      return res.data.data
    },
    refetchInterval: (query) =>
      query.state.data?.sources.some((s) => s.status === 'running') ? 3_000 : 30_000,
  })
  return { syncStatus: data, ...rest }
}

export function useTriggerSync() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (source: SyncSourceKey | 'all') => {
      const res = await apiClient.post<ApiResponse<SyncTriggerData>>('/themes/sync', { source })
      return res.data.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['themes', 'sync', 'status'] }),
  })
}

// ---------------------------------------------------------------------------
// Theme hooks
// ---------------------------------------------------------------------------
export function useThemes() {
  return useQuery({
    queryKey: ['themes', 'list'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<{ themes: Theme[]; last_scored_at: string | null }>>('/themes/')
      return res.data.data
    },
    refetchInterval: 60_000,
  })
}

export function useTrendingThemes() {
  return useQuery({
    queryKey: ['themes', 'trending'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<{ themes: Theme[] }>>('/themes/trending')
      return res.data.data.themes
    },
    refetchInterval: 60_000,
  })
}

export function useCoolingThemes() {
  return useQuery({
    queryKey: ['themes', 'cooling'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<{ themes: Theme[] }>>('/themes/cooling')
      return res.data.data.themes
    },
  })
}

export function useThemeDetail(slug: string | null) {
  return useQuery({
    queryKey: ['themes', 'detail', slug],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<ThemeDetail>>(`/themes/${slug}`)
      return res.data.data
    },
    enabled: !!slug,
  })
}

export function useInsiderFeed(days = 14) {
  return useQuery({
    queryKey: ['themes', 'signals', 'insider', days],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<{ signals: InsiderSignal[] }>>(
        `/themes/signals/insider?days=${days}`
      )
      return res.data.data.signals
    },
    refetchInterval: 120_000,
  })
}

export function useCongressFeed() {
  return useQuery({
    queryKey: ['themes', 'signals', 'congress'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<{ signals: InsiderSignal[] }>>('/themes/signals/congress')
      return res.data.data.signals
    },
  })
}

export function useContractFeed() {
  return useQuery({
    queryKey: ['themes', 'signals', 'contracts'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<{ signals: ContractSignal[] }>>('/themes/signals/contracts')
      return res.data.data.signals
    },
  })
}

// ---------------------------------------------------------------------------
// Pipeline hooks (public — orchestrates the full collection + scoring run)
// ---------------------------------------------------------------------------
export interface PipelineStatus {
  status: 'idle' | 'running' | 'done' | 'error'
  current_step: string
  step_label: string
  last_run: string | null
  started_at: string | null
  error: string | null
}

export function usePipelineStatus() {
  return useQuery({
    queryKey: ['themes', 'pipeline', 'status'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<PipelineStatus>>('/themes/pipeline/status')
      return res.data.data
    },
    refetchInterval: (q) => q.state.data?.status === 'running' ? 3_000 : 15_000,
  })
}

export function useTriggerPipeline() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post<ApiResponse<{ triggered: boolean; reason?: string }>>(
        '/themes/pipeline/run'
      )
      return res.data.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['themes', 'pipeline'] }),
  })
}

// ---------------------------------------------------------------------------
// Watchlist hooks (AUTH required)
// ---------------------------------------------------------------------------
export interface WatchlistItem {
  theme_id: string
  slug: string
  name: string
  added_at: string
}

export function useWatchlist() {
  return useQuery({
    queryKey: ['themes', 'watchlist'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<{ items: WatchlistItem[] }>>('/themes/watchlist')
      return res.data.data?.items ?? []
    },
  })
}

export function useAddToWatchlist() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (slug: string) => {
      const res = await apiClient.post<ApiResponse<{ added: boolean }>>(`/themes/watchlist/${slug}`)
      return res.data.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['themes', 'watchlist'] }),
  })
}

export function useRemoveFromWatchlist() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (slug: string) => {
      await apiClient.delete(`/themes/watchlist/${slug}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['themes', 'watchlist'] }),
  })
}
