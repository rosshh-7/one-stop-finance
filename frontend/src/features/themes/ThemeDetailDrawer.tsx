import { X, TrendingUp, TrendingDown, Users, DollarSign, Shield, FileText, BarChart2, Bookmark, BookmarkCheck, Eye, Building2, Zap, FlaskConical } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { useThemeDetail, useWatchlist, useAddToWatchlist, useRemoveFromWatchlist, type Theme } from './api'

interface Props {
  theme: Theme | null
  onClose: () => void
}

const LIFECYCLE_VARIANT: Record<string, 'green' | 'blue' | 'amber' | 'red' | 'cyan' | 'default'> = {
  EMERGING: 'cyan',
  BUILDING: 'blue',
  PEAK:     'green',
  FADING:   'amber',
  COOLING:  'red',
  STABLE:   'default',
}

function fmt(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

function MiniChart({ history }: { history: { score: number; scored_at: string }[] }) {
  if (history.length < 2) return (
    <p className="text-xs text-[var(--color-text-secondary)]">Not enough history yet</p>
  )

  const max = Math.max(...history.map((h) => h.score), 10)
  const w = 260
  const h = 60
  const pts = history.map((p, i) => ({
    x: (i / (history.length - 1)) * w,
    y: h - (p.score / max) * h,
  }))
  const path = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')

  return (
    <svg width={w} height={h} className="overflow-visible">
      <path d={path} stroke="#3b82f6" strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      {pts.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill="#3b82f6" />
      ))}
    </svg>
  )
}

const CONFIDENCE_VARIANT: Record<string, 'green' | 'amber' | 'red'> = {
  high: 'green', medium: 'amber', low: 'red',
}

export function ThemeDetailDrawer({ theme, onClose }: Props) {
  const { data: detail, isLoading } = useThemeDetail(theme?.slug ?? null)
  const { data: watchlist } = useWatchlist()
  const addToWatchlist = useAddToWatchlist()
  const removeFromWatchlist = useRemoveFromWatchlist()

  if (!theme) return null

  const s = theme.score
  const lifecycle = s?.lifecycle_stage ?? 'STABLE'
  const isWatching = watchlist?.some((w) => w.slug === theme.slug) ?? false

  const handleWatchToggle = () => {
    if (isWatching) {
      removeFromWatchlist.mutate(theme.slug)
    } else {
      addToWatchlist.mutate(theme.slug)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Drawer */}
      <div className="relative w-full max-w-md bg-[var(--color-bg-base)] border-l border-[var(--color-border)] overflow-y-auto flex flex-col h-full">
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-[var(--color-border)] sticky top-0 bg-[var(--color-bg-base)] z-10">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-lg font-bold text-[var(--color-text-primary)] truncate">{theme.name}</h3>
              <Badge variant={LIFECYCLE_VARIANT[lifecycle] ?? 'default'}>{lifecycle}</Badge>
            </div>
            <p className="text-sm text-[var(--color-text-secondary)]">{theme.description}</p>
          </div>
          <div className="flex items-center gap-1 ml-2 shrink-0">
            <button
              onClick={handleWatchToggle}
              className={`p-1.5 rounded hover:bg-[var(--color-bg-elevated)] transition-colors ${isWatching ? 'text-blue-400' : 'text-[var(--color-text-secondary)]'}`}
              title={isWatching ? 'Remove from watchlist' : 'Add to watchlist'}
            >
              {isWatching ? <BookmarkCheck className="h-5 w-5" /> : <Bookmark className="h-5 w-5" />}
            </button>
            <button onClick={onClose} className="p-1 rounded hover:bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)]">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <Spinner />
          </div>
        ) : (
          <div className="flex-1 p-5 space-y-6">
            {/* Score block */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-[var(--color-bg-elevated)] rounded-lg p-3">
                <p className="text-xs text-[var(--color-text-secondary)] mb-1">Score</p>
                <p className="text-2xl font-bold text-[var(--color-text-primary)]">{Math.round(s?.score ?? 0)}</p>
              </div>
              <div className="bg-[var(--color-bg-elevated)] rounded-lg p-3">
                <p className="text-xs text-[var(--color-text-secondary)] mb-1">Velocity</p>
                <div className="flex items-center gap-1">
                  {(s?.velocity ?? 0) >= 0
                    ? <TrendingUp className="h-4 w-4 text-green-400" />
                    : <TrendingDown className="h-4 w-4 text-red-400" />
                  }
                  <span className={`text-2xl font-bold ${(s?.velocity ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {(s?.velocity ?? 0) > 0 ? '+' : ''}{(s?.velocity ?? 0).toFixed(0)}
                  </span>
                </div>
              </div>
            </div>

            {/* Signal breakdown */}
            <div>
              <p className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-2">
                Signals
              </p>
              <div className="space-y-2">
                {(s?.unique_companies_buying ?? 0) > 0 && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-green-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">Companies buying</span>
                    </div>
                    <span className="text-sm font-semibold text-green-400">{s!.unique_companies_buying}</span>
                  </div>
                )}
                {(s?.total_value_accumulated ?? 0) > 0 && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <DollarSign className="h-4 w-4 text-blue-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">Total accumulated</span>
                    </div>
                    <span className="text-sm font-semibold text-blue-400">{fmt(s!.total_value_accumulated)}</span>
                  </div>
                )}
                {s?.congress_signal && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4 text-purple-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">Congressional trades</span>
                    </div>
                    <Badge variant="purple">Corroborated</Badge>
                  </div>
                )}
                {(s?.contracts_count ?? 0) > 0 && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-amber-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">Gov contracts</span>
                    </div>
                    <span className="text-sm font-semibold text-amber-400">{s!.contracts_count}</span>
                  </div>
                )}
                {(s?.options_anomaly ?? 0) >= 1.5 && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <BarChart2 className="h-4 w-4 text-cyan-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">Options anomaly</span>
                    </div>
                    <span className="text-sm font-semibold text-cyan-400">{s!.options_anomaly!.toFixed(1)}x vol</span>
                  </div>
                )}
                {(s?.signal_breakdown?.etf_vol_ratio ?? 0) >= 1.5 && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <BarChart2 className="h-4 w-4 text-cyan-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">ETF flow ({theme.benchmark_etf})</span>
                    </div>
                    <span className="text-sm font-semibold text-cyan-400">
                      {s!.signal_breakdown!.etf_vol_ratio!.toFixed(2)}x vol
                      {(s!.signal_breakdown!.etf_price_change_pct ?? 0) !== 0 && (
                        <span className="ml-1 text-xs text-[var(--color-text-secondary)]">
                          ({(s!.signal_breakdown!.etf_price_change_pct ?? 0) > 0 ? '+' : ''}{(s!.signal_breakdown!.etf_price_change_pct ?? 0).toFixed(1)}%)
                        </span>
                      )}
                    </span>
                  </div>
                )}
                {s?.signal_breakdown?.etf_put_call_ratio != null && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <BarChart2 className="h-4 w-4 text-blue-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">Put/Call ratio</span>
                    </div>
                    <span className={`text-sm font-semibold ${s.signal_breakdown.etf_put_call_ratio < 0.75 ? 'text-green-400' : 'text-[var(--color-text-secondary)]'}`}>
                      {s.signal_breakdown.etf_put_call_ratio.toFixed(2)}
                    </span>
                  </div>
                )}
                {s?.sentiment_signal && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-green-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">News sentiment</span>
                    </div>
                    <span className="text-sm font-semibold text-green-400">
                      {(s.signal_breakdown?.sentiment_score ?? 0) > 0 ? '+' : ''}
                      {(s.signal_breakdown?.sentiment_score ?? 0).toFixed(2)}
                    </span>
                  </div>
                )}
                {(s?.signal_breakdown?.activist_stake_count ?? 0) > 0 && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <Eye className="h-4 w-4 text-purple-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">Activist stakes (13D/G)</span>
                    </div>
                    <span className="text-sm font-semibold text-purple-400">{s!.signal_breakdown!.activist_stake_count} new</span>
                  </div>
                )}
                {(s?.signal_breakdown?.institutional_new_positions ?? 0) > 0 && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-blue-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">New institutional positions</span>
                    </div>
                    <span className="text-sm font-semibold text-blue-400">{s!.signal_breakdown!.institutional_new_positions}</span>
                  </div>
                )}
                {(s?.signal_breakdown?.ai_ecosystem_count ?? 0) > 0 && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <Zap className="h-4 w-4 text-yellow-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">AI ecosystem deals</span>
                    </div>
                    <span className="text-sm font-semibold text-yellow-400">{s!.signal_breakdown!.ai_ecosystem_count}</span>
                  </div>
                )}
                {s?.signal_breakdown?.short_high_and_buying && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-orange-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">Short squeeze setup</span>
                    </div>
                    <Badge variant="amber">High short + buying</Badge>
                  </div>
                )}
                {(s?.signal_breakdown?.nih_grant_count ?? 0) > 0 && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <FlaskConical className="h-4 w-4 text-green-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">NIH grants</span>
                    </div>
                    <span className="text-sm font-semibold text-green-400">{s!.signal_breakdown!.nih_grant_count} recent</span>
                  </div>
                )}
                {(s?.signal_breakdown?.signals_fired ?? 0) >= 4 && (
                  <div className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      <BarChart2 className="h-4 w-4 text-amber-400" />
                      <span className="text-sm text-[var(--color-text-primary)]">Convergence</span>
                    </div>
                    <Badge variant="amber">
                      {s!.signal_breakdown!.signals_fired} signals · +{s!.signal_breakdown!.convergence_bonus}
                    </Badge>
                  </div>
                )}
              </div>
            </div>

            {/* Synthesis (Claude Sonnet daily thesis) */}
            {s?.thesis && (
              <div className="bg-[var(--color-bg-elevated)] rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">
                    AI Thesis
                  </p>
                  {s.confidence && (
                    <Badge variant={CONFIDENCE_VARIANT[s.confidence] ?? 'default'}>
                      {s.confidence} confidence
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">{s.thesis}</p>
                {s.watch_for && (
                  <div className="border-t border-[var(--color-border)] pt-3">
                    <p className="text-xs text-[var(--color-text-secondary)] mb-1">Watch for next week</p>
                    <p className="text-sm text-[var(--color-text-primary)]">{s.watch_for}</p>
                  </div>
                )}
              </div>
            )}

            {/* Buying tickers */}
            {(s?.signal_breakdown?.buying_tickers ?? []).length > 0 && (
              <div>
                <p className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-2">
                  Insider Buying
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {s!.signal_breakdown!.buying_tickers.map((sym) => (
                    <span key={sym} className="text-xs font-mono bg-green-500/10 text-green-400 px-2 py-0.5 rounded-full border border-green-500/20">
                      {sym}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Selling tickers */}
            {(s?.signal_breakdown?.selling_tickers ?? []).length > 0 && (
              <div>
                <p className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-2">
                  Insider Selling
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {s!.signal_breakdown!.selling_tickers.map((sym) => (
                    <span key={sym} className="text-xs font-mono bg-red-500/10 text-red-400 px-2 py-0.5 rounded-full border border-red-500/20">
                      {sym}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 12-week chart */}
            <div>
              <p className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-3">
                12-Week Score History
              </p>
              <MiniChart history={detail?.history ?? []} />
            </div>

            {/* All theme tickers */}
            {detail && detail.tickers.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-2">
                  All Theme Tickers ({detail.tickers.length})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {detail.tickers.map((tt) => (
                    <span
                      key={tt.symbol}
                      title={tt.company_name ?? tt.symbol}
                      className="text-xs font-mono bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] px-2 py-0.5 rounded border border-[var(--color-border)]"
                    >
                      {tt.symbol}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
