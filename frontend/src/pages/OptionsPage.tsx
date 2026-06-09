import { useState } from 'react'
import { LineChart, Search, TrendingUp, TrendingDown } from 'lucide-react'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import {
  useOptionsScanner,
  useOptionsChain,
  type OptionContract,
  type StockScore,
} from '@/features/options/hooks'
import { cn } from '@/lib/utils'

export function OptionsPage() {
  const [input, setInput] = useState('')
  const [symbol, setSymbol] = useState('')
  const [expiry, setExpiry] = useState<string | undefined>(undefined)

  const { data: scanner, isLoading: scanLoading } = useOptionsScanner()
  const { data: chain, isLoading: chainLoading, isError: chainError } = useOptionsChain(symbol, expiry)

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    const sym = input.trim().toUpperCase()
    if (sym) {
      setSymbol(sym)
      setExpiry(undefined)
    }
  }

  function handleScannerClick(sym: string) {
    setInput(sym)
    setSymbol(sym)
    setExpiry(undefined)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <LineChart className="h-6 w-6 text-cyan-400" />
        <div>
          <h2 className="text-xl font-bold text-[var(--color-text-primary)]">Options Chain Analysis</h2>
          <p className="text-sm text-[var(--color-text-secondary)]">
            Options-based bullish / bearish signals · search any ticker for the full chain
          </p>
        </div>
      </div>

      {/* ── Scanner panels ── */}
      {scanLoading && (
        <div className="flex items-center gap-3 py-4 text-sm text-[var(--color-text-muted)]">
          <Spinner className="h-4 w-4" />
          Scanning {40} stocks for options signals…
        </div>
      )}

      {scanner && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <ScannerPanel
            title="Top 10 Bullish"
            icon={<TrendingUp className="h-4 w-4 text-emerald-400" />}
            stocks={scanner.bullish}
            direction="bullish"
            onSelect={handleScannerClick}
            scannedAt={scanner.scanned_at}
          />
          <ScannerPanel
            title="Top 10 Bearish"
            icon={<TrendingDown className="h-4 w-4 text-red-400" />}
            stocks={scanner.bearish}
            direction="bearish"
            onSelect={handleScannerClick}
            scannedAt={scanner.scanned_at}
          />
        </div>
      )}

      {/* ── Search bar ── */}
      <div className="border-t border-[var(--color-border)] pt-6">
        <p className="mb-3 text-sm font-medium text-[var(--color-text-secondary)]">
          Search any ticker for the full options chain
        </p>
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. TSLA, NVDA, SPY…"
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] py-2 pl-9 pr-3 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent-blue)]"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
          >
            Load Chain
          </button>
        </form>
      </div>

      {/* ── Chain loading / error ── */}
      {chainLoading && symbol && (
        <div className="flex justify-center py-12">
          <Spinner className="h-7 w-7" />
        </div>
      )}

      {chainError && symbol && (
        <Card>
          <p className="py-6 text-center text-sm text-red-400">
            No options data found for <span className="font-bold">{symbol}</span>. Check the ticker and try again.
          </p>
        </Card>
      )}

      {/* ── Full chain ── */}
      {chain && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <MetricCard label="Underlying" value={`$${chain.underlying_price.toLocaleString()}`} />
            <MetricCard
              label="Max Pain"
              value={`$${chain.max_pain.toLocaleString()}`}
              sub={chain.max_pain >= chain.underlying_price ? '▲ above spot' : '▼ below spot'}
              subColor={chain.max_pain >= chain.underlying_price ? 'text-emerald-400' : 'text-red-400'}
            />
            <MetricCard
              label="Put/Call Ratio"
              value={chain.put_call_ratio.toFixed(3)}
              sub={chain.put_call_ratio > 1 ? 'Bearish tilt' : 'Bullish tilt'}
              subColor={chain.put_call_ratio > 1 ? 'text-red-400' : 'text-emerald-400'}
            />
            <MetricCard label="Contracts" value={chain.total_contracts.toLocaleString()} sub={chain.expiry} />
          </div>

          <div className="flex gap-1.5 flex-wrap">
            {chain.expiries.map((exp) => (
              <button
                key={exp}
                onClick={() => setExpiry(exp)}
                className={cn(
                  'rounded-md border px-3 py-1 text-xs font-medium transition-colors',
                  (expiry ?? chain.expiry) === exp
                    ? 'border-[var(--color-accent-blue)] bg-[var(--color-accent-blue)]/15 text-[var(--color-accent-blue)]'
                    : 'border-[var(--color-border)] bg-[var(--color-bg-card)] text-[var(--color-text-secondary)] hover:border-[var(--color-accent-blue)]/50',
                )}
              >
                {exp}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <ContractTable title="Calls" contracts={chain.calls} type="call" spot={chain.underlying_price} />
            <ContractTable title="Puts" contracts={chain.puts} type="put" spot={chain.underlying_price} />
          </div>
        </>
      )}
    </div>
  )
}

/* ── Scanner panel ───────────────────────────────────────────────── */
function ScannerPanel({
  title,
  icon,
  stocks,
  direction,
  onSelect,
  scannedAt,
}: {
  title: string
  icon: React.ReactNode
  stocks: StockScore[]
  direction: 'bullish' | 'bearish'
  onSelect: (sym: string) => void
  scannedAt: string
}) {
  const badgeVariant = direction === 'bullish' ? ('cyan' as const) : ('red' as const)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          {icon}
          <CardTitle>{title}</CardTitle>
        </div>
        <span className="text-[10px] text-[var(--color-text-muted)]">
          {new Date(scannedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </CardHeader>

      {stocks.length === 0 && (
        <p className="py-4 text-center text-sm text-[var(--color-text-muted)]">No clear signals right now.</p>
      )}

      {/* Column headers */}
      <div className="mb-1 grid grid-cols-[1rem_5rem_1fr_1fr_3rem] gap-x-3 px-2 text-[10px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
        <span>#</span>
        <span>Ticker</span>
        <span>Current</span>
        <span>Forecast</span>
        <span className="text-right">Score</span>
      </div>

      <div className="space-y-1">
        {stocks.map((s, i) => {
          const isBull = direction === 'bullish'
          const priceColor = isBull ? 'text-emerald-400' : 'text-red-400'
          const moveSign = s.max_pain_pct >= 0 ? '+' : ''
          const fmt = (n: number) =>
            n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

          return (
            <button
              key={s.symbol}
              onClick={() => onSelect(s.symbol)}
              className="grid w-full grid-cols-[1rem_5rem_1fr_1fr_3rem] items-center gap-x-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-[var(--color-bg-elevated)]"
            >
              {/* Rank */}
              <span className="text-[10px] font-bold text-[var(--color-text-muted)]">{i + 1}</span>

              {/* Symbol + signal */}
              <div>
                <p className="text-sm font-bold text-[var(--color-text-primary)]">{s.symbol}</p>
                <Badge variant={badgeVariant} className="mt-0.5 text-[9px]">{s.signal}</Badge>
              </div>

              {/* Current price */}
              <div>
                <p className="text-[10px] text-[var(--color-text-muted)]">Now</p>
                <p className="text-sm font-semibold text-[var(--color-text-primary)]">
                  ${fmt(s.underlying_price)}
                </p>
              </div>

              {/* Forecast price */}
              <div>
                <p className="text-[10px] text-[var(--color-text-muted)]">Target</p>
                <p className={cn('text-sm font-bold', priceColor)}>${fmt(s.max_pain)}</p>
                <p className={cn('text-[10px] font-semibold', priceColor)}>
                  {moveSign}{s.max_pain_pct.toFixed(1)}%
                </p>
              </div>

              {/* Score */}
              <span className={cn('text-right text-xs font-bold', priceColor)}>
                {s.score > 0 ? '+' : ''}{s.score}
              </span>
            </button>
          )
        })}
      </div>
    </Card>
  )
}

/* ── Metric card ─────────────────────────────────────────────────── */
function MetricCard({
  label,
  value,
  sub,
  subColor = 'text-[var(--color-text-muted)]',
}: {
  label: string
  value: string
  sub?: string
  subColor?: string
}) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">{label}</p>
      <p className="mt-1 text-xl font-bold text-[var(--color-text-primary)]">{value}</p>
      {sub && <p className={cn('mt-0.5 text-xs', subColor)}>{sub}</p>}
    </Card>
  )
}

/* ── Contracts table ─────────────────────────────────────────────── */
function ContractTable({
  title,
  contracts,
  type,
  spot,
}: {
  title: string
  contracts: OptionContract[]
  type: 'call' | 'put'
  spot: number
}) {
  const accentColor = type === 'call' ? 'text-emerald-400' : 'text-red-400'
  const badgeVariant = type === 'call' ? ('cyan' as const) : ('red' as const)

  return (
    <Card>
      <CardHeader>
        <CardTitle className={accentColor}>{title}</CardTitle>
        <Badge variant={badgeVariant}>{contracts.length} contracts</Badge>
      </CardHeader>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[var(--color-border)] text-[var(--color-text-muted)]">
              {['Strike', 'Bid', 'Ask', 'Last', 'Vol', 'OI', 'IV%', 'Δ Delta'].map((h) => (
                <th key={h} className="py-2 pr-3 text-left font-medium last:pr-0">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {contracts.map((c) => (
              <ContractRow key={c.strike} contract={c} spot={spot} />
            ))}
            {contracts.length === 0 && (
              <tr>
                <td colSpan={8} className="py-6 text-center text-[var(--color-text-muted)]">No contracts</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

function ContractRow({ contract: c, spot }: { contract: OptionContract; spot: number }) {
  const nearMoney = spot > 0 && Math.abs(c.strike - spot) / spot < 0.02
  return (
    <tr className={cn(
      'transition-colors hover:bg-[var(--color-bg-elevated)]',
      c.in_the_money && 'bg-[var(--color-bg-elevated)]/60',
      nearMoney && 'ring-1 ring-inset ring-[var(--color-accent-blue)]/30',
    )}>
      <td className="py-1.5 pr-3 font-semibold text-[var(--color-text-primary)]">
        {c.in_the_money && <span className="mr-1 text-[10px] text-amber-400">●</span>}
        {c.strike.toFixed(0)}
      </td>
      <td className="py-1.5 pr-3 text-[var(--color-text-secondary)]">{c.bid.toFixed(2)}</td>
      <td className="py-1.5 pr-3 text-[var(--color-text-secondary)]">{c.ask.toFixed(2)}</td>
      <td className="py-1.5 pr-3 text-[var(--color-text-primary)]">{c.last.toFixed(2)}</td>
      <td className="py-1.5 pr-3 text-[var(--color-text-muted)]">{c.volume.toLocaleString()}</td>
      <td className="py-1.5 pr-3 text-[var(--color-text-muted)]">{c.open_interest.toLocaleString()}</td>
      <td className={cn(
        'py-1.5 pr-3 font-medium',
        c.implied_volatility > 60 ? 'text-red-400' : c.implied_volatility > 30 ? 'text-amber-400' : 'text-emerald-400',
      )}>
        {c.implied_volatility.toFixed(1)}%
      </td>
      <td className={cn('py-1.5 font-medium', c.delta > 0 ? 'text-emerald-400' : 'text-red-400')}>
        {c.delta > 0 ? '+' : ''}{c.delta.toFixed(3)}
      </td>
    </tr>
  )
}
