import { useState } from 'react'
import { Activity, RefreshCw, TrendingUp, TrendingDown, Minus, Search } from 'lucide-react'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { usePricePrediction, useRefreshPrediction } from '@/features/onchain/hooks'
import type { Direction, PricePrediction, PredictionSignal } from '@/features/onchain/types'
import { cn } from '@/lib/utils'

export function OnchainPage() {
  const [input, setInput] = useState('')
  const [symbol, setSymbol] = useState<string | null>(null)

  const { data, isLoading, error } = usePricePrediction(symbol)
  const refresh = useRefreshPrediction(symbol)

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    const clean = input.trim().toUpperCase()
    if (clean) setSymbol(clean)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Activity className="h-6 w-6 text-purple-400" />
        <div>
          <h2 className="text-xl font-bold text-[var(--color-text-primary)]">
            Options Chain Price Prediction
          </h2>
          <p className="text-sm text-[var(--color-text-secondary)]">
            Put/call ratio · max pain · GEX · RSI · MACD — 1-week horizon
          </p>
        </div>
      </div>

      {/* Ticker search */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-text-muted)]" />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter ticker — AAPL, TSLA…"
            className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] pl-9 pr-4 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent-blue)]"
          />
        </div>
        <button
          type="submit"
          className="rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
        >
          Analyze
        </button>
      </form>

      {isLoading && (
        <div className="flex items-center gap-3 text-[var(--color-text-secondary)] text-sm">
          <Spinner />
          <span>Fetching options chain and computing signals…</span>
        </div>
      )}

      {error && (
        <Card className="border-red-500/30">
          <p className="text-sm text-red-400">
            Could not load prediction for <strong>{symbol}</strong>. The ticker may not have listed
            options, or the market data is temporarily unavailable.
          </p>
        </Card>
      )}

      {data && <PredictionDashboard data={data} onRefresh={() => refresh.mutate()} refreshing={refresh.isPending} />}

      {!symbol && !isLoading && (
        <Card className="text-center py-10">
          <Activity className="h-10 w-10 text-[var(--color-text-muted)] mx-auto mb-3" />
          <p className="text-sm text-[var(--color-text-secondary)]">
            Enter a ticker above to generate a prediction
          </p>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">
            Works on any US-listed stock or ETF with active options (AAPL, NVDA, SPY…)
          </p>
        </Card>
      )}
    </div>
  )
}

function PredictionDashboard({
  data,
  onRefresh,
  refreshing,
}: {
  data: PricePrediction
  onRefresh: () => void
  refreshing: boolean
}) {
  return (
    <div className="space-y-4">
      {/* Top row: direction gauge + options snapshot */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DirectionCard data={data} onRefresh={onRefresh} refreshing={refreshing} />
        {data.options && <OptionsCard options={data.options} maxPain={data.max_pain} />}
      </div>

      {/* Support / resistance */}
      {(data.support || data.resistance) && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricTile label="Current Price" value={`$${data.current_price.toFixed(2)}`} />
          {data.support && <MetricTile label="20d Support" value={`$${data.support.toFixed(2)}`} color="green" />}
          {data.resistance && <MetricTile label="20d Resistance" value={`$${data.resistance.toFixed(2)}`} color="red" />}
          {data.max_pain && <MetricTile label="Max Pain" value={`$${data.max_pain.toFixed(2)}`} color="amber" />}
        </div>
      )}

      {/* Signals breakdown */}
      <SignalsTable signals={data.signals} />
    </div>
  )
}

function DirectionCard({
  data,
  onRefresh,
  refreshing,
}: {
  data: PricePrediction
  onRefresh: () => void
  refreshing: boolean
}) {
  const { direction, confidence, bull_score, bear_score, symbol, horizon, cached_at } = data

  return (
    <Card>
      <CardHeader>
        <CardTitle>{symbol} · {horizon} Prediction</CardTitle>
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
          title="Refresh prediction"
        >
          <RefreshCw className={cn('h-4 w-4', refreshing && 'animate-spin')} />
        </button>
      </CardHeader>

      <div className="flex items-center gap-5 mt-2">
        <DirectionIcon direction={direction} size="lg" />
        <div>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'text-2xl font-bold',
                direction === 'bullish' && 'text-green-400',
                direction === 'bearish' && 'text-red-400',
                direction === 'neutral' && 'text-amber-400',
              )}
            >
              {direction.toUpperCase()}
            </span>
            <DirectionBadge direction={direction} />
          </div>
          <p className="text-sm text-[var(--color-text-secondary)] mt-0.5">
            {confidence.toFixed(1)}% confidence
          </p>
        </div>
      </div>

      {/* Bull / Bear bar */}
      <div className="mt-4">
        <div className="flex justify-between text-xs text-[var(--color-text-muted)] mb-1">
          <span>Bearish {bear_score.toFixed(0)}%</span>
          <span>Bullish {bull_score.toFixed(0)}%</span>
        </div>
        <div className="h-2 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden flex">
          <div
            className="h-full bg-red-500/70 transition-all"
            style={{ width: `${bear_score}%` }}
          />
          <div className="flex-1" />
          <div
            className="h-full bg-green-500/70 transition-all"
            style={{ width: `${bull_score}%` }}
          />
        </div>
      </div>

      <p className="text-xs text-[var(--color-text-muted)] mt-3">
        Updated {new Date(cached_at).toLocaleTimeString()}
      </p>
    </Card>
  )
}

function OptionsCard({
  options,
  maxPain,
}: {
  options: NonNullable<PricePrediction['options']>
  maxPain: number | null
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Options Snapshot · {options.expiry}</CardTitle>
      </CardHeader>
      <div className="grid grid-cols-2 gap-3">
        <OptionStat
          label="Put/Call Ratio"
          value={options.put_call_ratio.toFixed(3)}
          note={options.put_call_ratio < 0.7 ? 'bullish' : options.put_call_ratio > 1.0 ? 'bearish' : 'neutral'}
        />
        <OptionStat label="Call OI" value={fmtNum(options.total_call_oi)} />
        <OptionStat label="Put OI" value={fmtNum(options.total_put_oi)} />
        <OptionStat label="Avg Call IV" value={`${options.avg_call_iv.toFixed(1)}%`} />
        <OptionStat label="Avg Put IV" value={`${options.avg_put_iv.toFixed(1)}%`} />
        <OptionStat
          label="Net GEX"
          value={fmtNum(options.net_gex)}
          note={options.net_gex > 0 ? 'pinning' : 'volatile'}
        />
      </div>
    </Card>
  )
}

function SignalsTable({ signals }: { signals: PredictionSignal[] }) {
  if (!signals.length) return null
  return (
    <Card>
      <CardHeader>
        <CardTitle>Signal Breakdown</CardTitle>
      </CardHeader>
      <div className="space-y-2">
        {signals.map((sig) => (
          <div
            key={sig.name}
            className="flex items-center justify-between py-2 border-b border-[var(--color-border)] last:border-0"
          >
            <div className="flex items-center gap-2">
              <DirectionIcon direction={sig.direction} size="sm" />
              <span className="text-sm text-[var(--color-text-primary)]">{sig.name}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-[var(--color-text-muted)] font-mono">{sig.display_value}</span>
              <DirectionBadge direction={sig.direction} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

function MetricTile({
  label,
  value,
  color,
}: {
  label: string
  value: string
  color?: 'green' | 'red' | 'amber'
}) {
  return (
    <Card className="text-center py-3">
      <p className="text-xs text-[var(--color-text-muted)] mb-1">{label}</p>
      <p
        className={cn(
          'text-lg font-bold font-mono',
          color === 'green' && 'text-green-400',
          color === 'red' && 'text-red-400',
          color === 'amber' && 'text-amber-400',
          !color && 'text-[var(--color-text-primary)]',
        )}
      >
        {value}
      </p>
    </Card>
  )
}

function OptionStat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div>
      <p className="text-xs text-[var(--color-text-muted)]">{label}</p>
      <p className="text-sm font-mono font-semibold text-[var(--color-text-primary)]">{value}</p>
      {note && (
        <p
          className={cn(
            'text-xs',
            note === 'bullish' && 'text-green-400',
            note === 'bearish' && 'text-red-400',
            note === 'neutral' && 'text-amber-400',
            note === 'pinning' && 'text-blue-400',
            note === 'volatile' && 'text-purple-400',
          )}
        >
          {note}
        </p>
      )}
    </div>
  )
}

function DirectionIcon({ direction, size }: { direction: Direction; size: 'sm' | 'lg' }) {
  const cls = size === 'lg' ? 'h-10 w-10' : 'h-4 w-4'
  if (direction === 'bullish') return <TrendingUp className={cn(cls, 'text-green-400')} />
  if (direction === 'bearish') return <TrendingDown className={cn(cls, 'text-red-400')} />
  return <Minus className={cn(cls, 'text-amber-400')} />
}

function DirectionBadge({ direction }: { direction: Direction }) {
  if (direction === 'bullish') return <Badge variant="green">Bullish</Badge>
  if (direction === 'bearish') return <Badge variant="red">Bearish</Badge>
  return <Badge variant="amber">Neutral</Badge>
}

function fmtNum(n: number): string {
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(Math.round(n))
}
