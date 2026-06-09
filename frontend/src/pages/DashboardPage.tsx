import { useState } from 'react'
import { Flame, Users, Brain, LineChart, TrendingUp, Activity, Search, TrendingDown, Minus, RefreshCw, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { usePricePrediction, useRefreshPrediction } from '@/features/onchain/hooks'
import type { Direction } from '@/features/onchain/types'
import { cn } from '@/lib/utils'

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-[var(--color-text-primary)]">Market Overview</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">Real-time signals across all features</p>
      </div>

      {/* Market indices ticker */}
      <div className="flex gap-4 overflow-x-auto pb-1">
        {[
          { symbol: 'S&P 500', price: '5,432.10', change: '+0.82%', up: true },
          { symbol: 'NASDAQ', price: '17,891.33', change: '+1.24%', up: true },
          { symbol: 'DOW', price: '42,103.55', change: '-0.14%', up: false },
          { symbol: 'VIX', price: '14.23', change: '-3.21%', up: false },
          { symbol: 'Russell', price: '2,105.88', change: '+0.55%', up: true },
        ].map(({ symbol, price, change, up }) => (
          <div
            key={symbol}
            className="flex-shrink-0 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] px-4 py-2.5"
          >
            <p className="text-xs text-[var(--color-text-muted)]">{symbol}</p>
            <p className="text-sm font-semibold text-[var(--color-text-primary)]">{price}</p>
            <p className={`text-xs font-medium ${up ? 'text-green-400' : 'text-red-400'}`}>{change}</p>
          </div>
        ))}
      </div>

      {/* Feature summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <FeatureSummaryCard
          icon={<Flame className="h-4 w-4 text-amber-400" />}
          title="Theme Intelligence"
          value="3 ALERT"
          sub="AI, Defense, Biotech themes hot"
          href="/themes"
        />
        <FeatureSummaryCard
          icon={<Users className="h-4 w-4 text-blue-400" />}
          title="Insider Trades"
          value="12 buys"
          sub="$47M aggregate open market"
          href="/insiders"
        />
        <FeatureSummaryCard
          icon={<Brain className="h-4 w-4 text-purple-400" />}
          title="Sentiment"
          value="Bullish"
          sub="72% positive signal ratio"
          href="/sentiment"
        />
        <FeatureSummaryCard
          icon={<LineChart className="h-4 w-4 text-cyan-400" />}
          title="Options Flow"
          value="Unusual"
          sub="Semis showing vol spike"
          href="/options"
        />
        <FeatureSummaryCard
          icon={<TrendingUp className="h-4 w-4 text-green-400" />}
          title="Trend Reversal"
          value="8 signals"
          sub="Key support levels forming"
          href="/trend"
        />
        <FeatureSummaryCard
          icon={<Activity className="h-4 w-4 text-[var(--color-accent-blue)]" />}
          title="Real-Time Feed"
          value="Connected"
          sub="WebSocket live"
          href="/dashboard"
        />
      </div>

      {/* Options Chain Prediction widget */}
      <ChainPredictionWidget />

      {/* Coming soon placeholder for content */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity Feed</CardTitle>
        </CardHeader>
        <div className="space-y-3">
          {[
            { time: '2m ago', event: 'Insider Buy: NVDA — CEO $12.4M open market purchase', type: 'buy' },
            { time: '8m ago', event: 'Unusual Options: TSLA — 2,400 calls at $280 strike (10x avg volume)', type: 'options' },
            { time: '15m ago', event: 'Theme Alert: AI Infrastructure — 8 unique insiders buying this week', type: 'theme' },
            { time: '22m ago', event: 'Congress Trade: AMZN — Rep. Jane Smith bought $50K–$100K', type: 'congress' },
          ].map(({ time, event, type }) => (
            <div key={event} className="flex items-start gap-3 text-sm">
              <span className="flex-shrink-0 text-xs text-[var(--color-text-muted)] w-12">{time}</span>
              <Badge
                variant={type === 'buy' ? 'green' : type === 'options' ? 'cyan' : type === 'theme' ? 'amber' : 'blue'}
                className="flex-shrink-0 capitalize"
              >
                {type}
              </Badge>
              <span className="text-[var(--color-text-secondary)]">{event}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

function ChainPredictionWidget() {
  const [input, setInput] = useState('')
  const [symbol, setSymbol] = useState<string | null>('SPY')

  const { data, isLoading, error } = usePricePrediction(symbol)
  const refresh = useRefreshPrediction(symbol)

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    const clean = input.trim().toUpperCase()
    if (clean) { setSymbol(clean); setInput('') }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-purple-400" />
          <CardTitle>Options Chain Prediction</CardTitle>
        </div>
        <div className="flex items-center gap-2">
          <form onSubmit={handleSearch} className="flex gap-1.5">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-[var(--color-text-muted)]" />
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ticker…"
                className="w-28 rounded-md border border-[var(--color-border)] bg-[var(--color-bg-elevated)] pl-7 pr-2 py-1 text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent-blue)]"
              />
            </div>
            <button
              type="submit"
              className="rounded-md bg-[var(--color-accent-blue)] px-2.5 py-1 text-xs font-medium text-white hover:opacity-90"
            >
              Go
            </button>
          </form>
          {data && (
            <button
              onClick={() => refresh.mutate()}
              disabled={refresh.isPending}
              className="text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
            >
              <RefreshCw className={cn('h-3.5 w-3.5', refresh.isPending && 'animate-spin')} />
            </button>
          )}
        </div>
      </CardHeader>

      {isLoading && (
        <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)] py-4">
          <Spinner /> <span>Fetching options chain for {symbol}…</span>
        </div>
      )}

      {error && (
        <p className="text-xs text-red-400 py-2">
          No options data for <strong>{symbol}</strong> — try a different ticker.
        </p>
      )}

      {data && (
        <div className="space-y-4">
          {/* Direction + confidence + price row */}
          <div className="flex items-center gap-6 flex-wrap">
            <div className="flex items-center gap-2">
              <DirectionIcon direction={data.direction} />
              <div>
                <div className="flex items-center gap-2">
                  <span className={cn(
                    'text-xl font-bold',
                    data.direction === 'bullish' && 'text-green-400',
                    data.direction === 'bearish' && 'text-red-400',
                    data.direction === 'neutral'  && 'text-amber-400',
                  )}>
                    {data.symbol} — {data.direction.toUpperCase()}
                  </span>
                  <DirectionBadge direction={data.direction} />
                </div>
                <p className="text-xs text-[var(--color-text-muted)]">
                  {data.confidence.toFixed(1)}% confidence · 1-week horizon
                </p>
              </div>
            </div>

            <div className="flex gap-4 text-xs">
              <Stat label="Price"       value={`$${data.current_price.toFixed(2)}`} />
              {data.max_pain  && <Stat label="Max Pain"   value={`$${data.max_pain.toFixed(2)}`}  color="amber" />}
              {data.support   && <Stat label="Support"    value={`$${data.support.toFixed(2)}`}   color="green" />}
              {data.resistance && <Stat label="Resistance" value={`$${data.resistance.toFixed(2)}`} color="red" />}
              {data.options   && <Stat label="PCR"        value={data.options.put_call_ratio.toFixed(3)} color={data.options.put_call_ratio < 0.7 ? 'green' : data.options.put_call_ratio > 1.0 ? 'red' : 'amber'} />}
            </div>
          </div>

          {/* Bull / Bear bar */}
          <div>
            <div className="flex justify-between text-xs text-[var(--color-text-muted)] mb-1">
              <span>Bear {data.bear_score.toFixed(0)}%</span>
              <span>Bull {data.bull_score.toFixed(0)}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden flex">
              <div className="h-full bg-red-500/70" style={{ width: `${data.bear_score}%` }} />
              <div className="flex-1" />
              <div className="h-full bg-green-500/70" style={{ width: `${data.bull_score}%` }} />
            </div>
          </div>

          {/* Top 4 signals */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
            {data.signals.slice(0, 4).map(sig => (
              <div key={sig.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <SmallDirectionDot direction={sig.direction} />
                  <span className="text-[var(--color-text-secondary)]">{sig.name}</span>
                </div>
                <span className="text-[var(--color-text-muted)] font-mono">{sig.display_value}</span>
              </div>
            ))}
          </div>

          <Link
            to="/onchain"
            className="flex items-center gap-1 text-xs text-[var(--color-accent-blue)] hover:underline"
          >
            Full analysis <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      )}
    </Card>
  )
}

function DirectionIcon({ direction }: { direction: Direction }) {
  if (direction === 'bullish') return <TrendingUp className="h-7 w-7 text-green-400" />
  if (direction === 'bearish') return <TrendingDown className="h-7 w-7 text-red-400" />
  return <Minus className="h-7 w-7 text-amber-400" />
}

function DirectionBadge({ direction }: { direction: Direction }) {
  if (direction === 'bullish') return <Badge variant="green">Bullish</Badge>
  if (direction === 'bearish') return <Badge variant="red">Bearish</Badge>
  return <Badge variant="amber">Neutral</Badge>
}

function SmallDirectionDot({ direction }: { direction: Direction }) {
  return (
    <span className={cn(
      'inline-block h-1.5 w-1.5 rounded-full flex-shrink-0',
      direction === 'bullish' && 'bg-green-400',
      direction === 'bearish' && 'bg-red-400',
      direction === 'neutral'  && 'bg-amber-400',
    )} />
  )
}

function Stat({ label, value, color }: { label: string; value: string; color?: 'green' | 'red' | 'amber' }) {
  return (
    <div>
      <p className="text-[var(--color-text-muted)]">{label}</p>
      <p className={cn(
        'font-mono font-semibold',
        color === 'green' && 'text-green-400',
        color === 'red'   && 'text-red-400',
        color === 'amber' && 'text-amber-400',
        !color            && 'text-[var(--color-text-primary)]',
      )}>
        {value}
      </p>
    </div>
  )
}

function FeatureSummaryCard({
  icon,
  title,
  value,
  sub,
  href,
}: {
  icon: React.ReactNode
  title: string
  value: string
  sub: string
  href: string
}) {
  return (
    <a href={href}>
      <Card className="hover:border-[var(--color-accent-blue)] transition-colors cursor-pointer">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            {icon}
            <span className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide">{title}</span>
          </div>
        </div>
        <p className="text-2xl font-bold text-[var(--color-text-primary)]">{value}</p>
        <p className="mt-1 text-xs text-[var(--color-text-muted)]">{sub}</p>
      </Card>
    </a>
  )
}
