import { Link } from 'react-router-dom'
import {
  Flame, Users, Brain, LineChart, TrendingUp, TrendingDown,
  Minus, ArrowRight, Wifi, WifiOff, Target,
} from 'lucide-react'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { useMarketSummary } from '@/features/landing/hooks'
import { useThemeIntelligence, useInsiderHighlights, type ThemeScore, type InsiderHighlight } from '@/features/dashboard/hooks'
import { useOptionsScanner, type StockScore } from '@/features/options/hooks'
import { useRealtimeStore } from '@/stores/realtime.store'
import { cn, formatPercent } from '@/lib/utils'

export function DashboardPage() {
  const wsConnected = useRealtimeStore((s) => s.wsConnected)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-[var(--color-text-primary)]">Market Overview</h2>
          <p className="text-sm text-[var(--color-text-secondary)]">Real-time signals across all features</p>
        </div>
        <div className={cn(
          'flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium',
          wsConnected
            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
            : 'border-[var(--color-border)] bg-[var(--color-bg-card)] text-[var(--color-text-muted)]',
        )}>
          {wsConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
          {wsConnected ? 'Live' : 'Connecting…'}
        </div>
      </div>

      <MarketIndicesStrip />
      <FeatureCards />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ThemeIntelligencePanel />
        <InsiderHighlightsPanel />
      </div>
      <PriceForecastPanel />
    </div>
  )
}

/* ── Market Indices ───────────────────────────────────────────────── */
function MarketIndicesStrip() {
  const { data: indices, isLoading } = useMarketSummary()

  if (isLoading && !indices) {
    return (
      <div className="flex gap-4 overflow-x-auto pb-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="flex-shrink-0 animate-pulse rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] px-4 py-2.5"
          >
            <div className="mb-1 h-2.5 w-12 rounded bg-[var(--color-bg-elevated)]" />
            <div className="mb-1 h-4 w-16 rounded bg-[var(--color-bg-elevated)]" />
            <div className="h-2.5 w-10 rounded bg-[var(--color-bg-elevated)]" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="flex gap-3 overflow-x-auto pb-1">
      {indices?.map((idx) => {
        const up = idx.change > 0
        const neutral = idx.change === 0
        return (
          <div
            key={idx.symbol}
            className="flex-shrink-0 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] px-4 py-2.5"
          >
            <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wide">{idx.short}</p>
            <p className="text-sm font-semibold text-[var(--color-text-primary)]">
              {idx.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
            <p className={cn(
              'flex items-center gap-0.5 text-xs font-medium',
              neutral ? 'text-[var(--color-text-muted)]' : up ? 'text-emerald-400' : 'text-red-400',
            )}>
              {neutral ? <Minus className="h-3 w-3" /> : up ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {formatPercent(idx.change_pct)}
            </p>
          </div>
        )
      })}
    </div>
  )
}

/* ── Feature Quick-Nav Cards ──────────────────────────────────────── */
function FeatureCards() {
  const { data: themes } = useThemeIntelligence()
  const { data: highlights } = useInsiderHighlights()

  const alertCount = themes?.filter((t) => t.level === 'alert').length ?? 0
  const insiderBuys = highlights?.filter((h) => h.transaction_type === 'buy').length ?? 0
  const totalInsiderValue = highlights?.reduce((sum, h) => sum + (h.transaction_type === 'buy' ? h.total_value : 0), 0) ?? 0

  const features = [
    {
      icon: <Flame className="h-4 w-4 text-amber-400" />,
      title: 'Theme Intelligence',
      value: alertCount > 0 ? `${alertCount} Alert${alertCount > 1 ? 's' : ''}` : themes ? 'No Alerts' : '—',
      sub: themes ? `${themes.filter(t => t.level === 'watch').length} watching, ${themes.filter(t => t.level === 'quiet').length} quiet` : 'Loading…',
      href: '/themes',
      badge: alertCount > 0 ? 'amber' as const : undefined,
    },
    {
      icon: <Users className="h-4 w-4 text-blue-400" />,
      title: 'Insider Trades',
      value: insiderBuys > 0 ? `${insiderBuys} buy${insiderBuys > 1 ? 's' : ''}` : highlights ? 'No buys' : '—',
      sub: totalInsiderValue > 0 ? `$${(totalInsiderValue / 1_000_000).toFixed(1)}M aggregate open market` : 'Loading…',
      href: '/insiders',
      badge: insiderBuys > 0 ? 'blue' as const : undefined,
    },
    {
      icon: <Brain className="h-4 w-4 text-purple-400" />,
      title: 'Sentiment',
      value: 'Live',
      sub: 'FinBERT scoring across headlines',
      href: '/sentiment',
    },
    {
      icon: <LineChart className="h-4 w-4 text-cyan-400" />,
      title: 'Options Flow',
      value: 'Live',
      sub: 'Unusual activity scanner active',
      href: '/options',
    },
    {
      icon: <TrendingUp className="h-4 w-4 text-green-400" />,
      title: 'Trend Reversal',
      value: 'Live',
      sub: 'Signal scanner running every 15 min',
      href: '/trend',
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {features.map(({ icon, title, value, sub, href, badge }) => (
        <Link key={href} to={href}>
          <Card className="hover:border-[var(--color-accent-blue)] transition-colors h-full">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                {icon}
                <span className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-secondary)]">{title}</span>
              </div>
              {badge && <Badge variant={badge} className="text-[10px]">•</Badge>}
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">{value}</p>
            <p className="mt-1 text-xs text-[var(--color-text-muted)]">{sub}</p>
          </Card>
        </Link>
      ))}
    </div>
  )
}

/* ── Theme Intelligence Panel ─────────────────────────────────────── */
function ThemeIntelligencePanel() {
  const { data: themes, isLoading, isError } = useThemeIntelligence()

  const levelConfig = {
    alert: { label: 'Alert', badgeVariant: 'red' as const, dot: 'bg-red-400' },
    watch: { label: 'Watch', badgeVariant: 'amber' as const, dot: 'bg-amber-400' },
    quiet: { label: 'Quiet', badgeVariant: 'default' as const, dot: 'bg-[var(--color-text-muted)]' },
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Flame className="h-4 w-4 text-amber-400" />
          <CardTitle>Theme Intelligence</CardTitle>
        </div>
        <Link
          to="/themes"
          className="flex items-center gap-1 text-xs text-[var(--color-accent-blue)] hover:underline"
        >
          All themes <ArrowRight className="h-3 w-3" />
        </Link>
      </CardHeader>

      {isLoading && !themes && (
        <div className="flex justify-center py-8">
          <Spinner className="h-6 w-6" />
        </div>
      )}

      {isError && (
        <p className="py-4 text-center text-sm text-[var(--color-text-muted)]">
          Unable to load themes right now.
        </p>
      )}

      {themes && (
        <div className="space-y-2.5">
          {themes
            .slice()
            .sort((a, b) => b.score - a.score)
            .slice(0, 6)
            .map((theme) => (
              <ThemeRow key={theme.slug} theme={theme} levelConfig={levelConfig} />
            ))}
        </div>
      )}
    </Card>
  )
}

function ThemeRow({
  theme,
  levelConfig,
}: {
  theme: ThemeScore
  levelConfig: Record<string, { label: string; badgeVariant: 'red' | 'amber' | 'default'; dot: string }>
}) {
  const cfg = levelConfig[theme.level]
  const barWidth = `${theme.score}%`

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 min-w-0">
        <div className="mb-1 flex items-center justify-between gap-2">
          <span className="truncate text-sm font-medium text-[var(--color-text-primary)]">{theme.name}</span>
          <div className="flex flex-shrink-0 items-center gap-2">
            <span className="text-xs font-semibold text-[var(--color-text-primary)]">{theme.score}</span>
            <Badge variant={cfg.badgeVariant}>{cfg.label}</Badge>
          </div>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--color-bg-elevated)]">
          <div
            className={cn(
              'h-full rounded-full transition-all',
              theme.level === 'alert' ? 'bg-red-400' : theme.level === 'watch' ? 'bg-amber-400' : 'bg-[var(--color-text-muted)]',
            )}
            style={{ width: barWidth }}
          />
        </div>
        <p className="mt-0.5 text-[10px] text-[var(--color-text-muted)]">
          {theme.unique_companies_buying} co. buying · {theme.benchmark_etf}
        </p>
      </div>
    </div>
  )
}

/* ── Insider Highlights Panel ─────────────────────────────────────── */
function InsiderHighlightsPanel() {
  const { data: highlights, isLoading, isError } = useInsiderHighlights()

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-blue-400" />
          <CardTitle>Top Insider Buys</CardTitle>
        </div>
        <Link
          to="/insiders"
          className="flex items-center gap-1 text-xs text-[var(--color-accent-blue)] hover:underline"
        >
          All trades <ArrowRight className="h-3 w-3" />
        </Link>
      </CardHeader>

      {isLoading && !highlights && (
        <div className="flex justify-center py-8">
          <Spinner className="h-6 w-6" />
        </div>
      )}

      {isError && (
        <p className="py-4 text-center text-sm text-[var(--color-text-muted)]">
          Unable to load insider data right now.
        </p>
      )}

      {highlights && (
        <div className="space-y-3">
          {highlights.slice(0, 5).map((h) => (
            <InsiderRow key={`${h.symbol}-${h.transaction_date}-${h.insider_name}`} highlight={h} />
          ))}
          {highlights.length === 0 && (
            <p className="py-4 text-center text-sm text-[var(--color-text-muted)]">No recent insider buys.</p>
          )}
        </div>
      )}
    </Card>
  )
}

function InsiderRow({ highlight: h }: { highlight: InsiderHighlight }) {
  const score = h.signal_score
  const scoreColor = score >= 70 ? 'text-emerald-400' : score >= 40 ? 'text-amber-400' : 'text-[var(--color-text-muted)]'
  const value = h.total_value >= 1_000_000
    ? `$${(h.total_value / 1_000_000).toFixed(1)}M`
    : `$${(h.total_value / 1_000).toFixed(0)}K`

  return (
    <a
      href={h.sec_filing_url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-3 rounded-lg p-2 hover:bg-[var(--color-bg-elevated)] transition-colors"
    >
      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-[var(--color-border)] bg-[var(--color-bg-elevated)]">
        <span className="text-xs font-bold text-[var(--color-text-primary)]">{h.symbol.slice(0, 3)}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-[var(--color-text-primary)]">{h.symbol}</span>
          <span className="text-sm font-bold text-emerald-400">{value}</span>
        </div>
        <p className="truncate text-xs text-[var(--color-text-muted)]">
          {h.insider_name} · {h.insider_title}
        </p>
      </div>
      <div className={cn('flex-shrink-0 text-xs font-semibold', scoreColor)}>
        {score}
      </div>
    </a>
  )
}

/* ── Price Forecast Panel ─────────────────────────────────────────── */
function PriceForecastPanel() {
  const { data: scanner, isLoading, isError } = useOptionsScanner()

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="h-5 w-5 text-cyan-400" />
          <div>
            <h3 className="text-base font-bold text-[var(--color-text-primary)]">Options-Implied Price Forecasts</h3>
            <p className="text-xs text-[var(--color-text-muted)]">Target = max pain level · updated every 15 min</p>
          </div>
        </div>
        <Link
          to="/options"
          className="flex items-center gap-1 text-xs text-[var(--color-accent-blue)] hover:underline"
        >
          Full chain analysis <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 py-4 text-sm text-[var(--color-text-muted)]">
          <Spinner className="h-4 w-4" /> Scanning 40 stocks…
        </div>
      )}

      {isError && (
        <p className="py-4 text-sm text-[var(--color-text-muted)]">Unable to load forecast data.</p>
      )}

      {scanner && (
        <div className="space-y-4">
          {/* Bullish */}
          <div>
            <div className="mb-2 flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-xs font-semibold uppercase tracking-wide text-emerald-400">Bullish targets</span>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {scanner.bullish.slice(0, 5).map((s) => (
                <ForecastCard key={s.symbol} stock={s} direction="bullish" />
              ))}
            </div>
          </div>

          {/* Bearish */}
          <div>
            <div className="mb-2 flex items-center gap-1.5">
              <TrendingDown className="h-3.5 w-3.5 text-red-400" />
              <span className="text-xs font-semibold uppercase tracking-wide text-red-400">Bearish targets</span>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {scanner.bearish.slice(0, 5).map((s) => (
                <ForecastCard key={s.symbol} stock={s} direction="bearish" />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ForecastCard({ stock: s, direction }: { stock: StockScore; direction: 'bullish' | 'bearish' }) {
  const isBull = direction === 'bullish'
  const moveColor = isBull ? 'text-emerald-400' : 'text-red-400'
  const borderColor = isBull ? 'border-emerald-500/20' : 'border-red-500/20'
  const bgColor = isBull ? 'bg-emerald-500/5' : 'bg-red-500/5'
  const barColor = isBull ? 'bg-emerald-400' : 'bg-red-400'
  const confidence = Math.min(100, Math.round(Math.abs(s.score)))
  const moveSign = s.max_pain_pct >= 0 ? '+' : ''

  const fmt = (n: number) =>
    n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

  return (
    <Link to="/options">
      <div className={cn(
        'rounded-xl border p-3 transition-colors hover:bg-[var(--color-bg-elevated)]',
        borderColor, bgColor,
      )}>
        {/* Header: ticker + badge */}
        <div className="mb-3 flex items-start justify-between gap-1">
          <span className="text-sm font-bold text-[var(--color-text-primary)]">{s.symbol}</span>
          <Badge variant={isBull ? 'cyan' : 'red'} className="text-[9px]">
            {isBull ? '▲' : '▼'}
          </Badge>
        </div>

        {/* Current price — large */}
        <div className="mb-1">
          <p className="text-[10px] text-[var(--color-text-muted)]">Current</p>
          <p className="text-lg font-bold text-[var(--color-text-primary)]">${fmt(s.underlying_price)}</p>
        </div>

        {/* Arrow */}
        <div className={cn('my-1 text-center text-base font-bold', moveColor)}>
          {isBull ? '↑' : '↓'}
        </div>

        {/* Forecast price — large + colored */}
        <div className="mb-3">
          <p className="text-[10px] text-[var(--color-text-muted)]">Forecast</p>
          <p className={cn('text-lg font-bold', moveColor)}>${fmt(s.max_pain)}</p>
          <p className={cn('text-xs font-semibold', moveColor)}>
            {moveSign}{s.max_pain_pct.toFixed(1)}% expected
          </p>
        </div>

        {/* Confidence bar */}
        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-[10px] text-[var(--color-text-muted)]">Confidence</span>
            <span className={cn('text-[10px] font-bold', moveColor)}>{confidence}%</span>
          </div>
          <div className="h-1 w-full overflow-hidden rounded-full bg-[var(--color-bg-elevated)]">
            <div className={cn('h-full rounded-full', barColor)} style={{ width: `${confidence}%` }} />
          </div>
        </div>
      </div>
    </Link>
  )
}
