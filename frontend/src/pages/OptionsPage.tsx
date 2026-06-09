import { useState } from 'react'
import { LineChart, Search } from 'lucide-react'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { useOptionsChain } from '@/features/options/hooks'
import type { OptionContract, OptionsChain } from '@/features/options/types'
import { cn } from '@/lib/utils'

export function OptionsPage() {
  const [input, setInput] = useState('')
  const [symbol, setSymbol] = useState<string | null>(null)
  const [expiry, setExpiry] = useState<string | undefined>()

  const { data, isLoading, error } = useOptionsChain(symbol, expiry)

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    const clean = input.trim().toUpperCase()
    if (clean) { setSymbol(clean); setExpiry(undefined) }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <LineChart className="h-6 w-6 text-cyan-400" />
        <div>
          <h2 className="text-xl font-bold text-[var(--color-text-primary)]">Options Chain</h2>
          <p className="text-sm text-[var(--color-text-secondary)]">
            Live calls & puts · IV · greeks · max pain · put/call ratio
          </p>
        </div>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative max-w-xs flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-text-muted)]" />
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Enter ticker — AAPL, TSLA, SPY…"
            className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] pl-9 pr-4 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent-blue)]"
          />
        </div>
        <button
          type="submit"
          className="rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
        >
          Load Chain
        </button>
      </form>

      {isLoading && (
        <div className="flex items-center gap-3 text-sm text-[var(--color-text-secondary)]">
          <Spinner /> Fetching options chain for {symbol}…
        </div>
      )}

      {error && (
        <Card className="border-red-500/30">
          <p className="text-sm text-red-400">
            No options data for <strong>{symbol}</strong>. Try a liquid ticker like AAPL, TSLA, or SPY.
          </p>
        </Card>
      )}

      {data && (
        <ChainView
          data={data}
          selectedExpiry={expiry ?? data.expiry}
          onExpiry={e => setExpiry(e)}
        />
      )}

      {!symbol && !isLoading && (
        <Card className="py-12 text-center">
          <LineChart className="h-10 w-10 text-[var(--color-text-muted)] mx-auto mb-3" />
          <p className="text-sm text-[var(--color-text-secondary)]">Enter a ticker to load its full options chain</p>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">Works with any US-listed stock or ETF (AAPL, NVDA, SPY…)</p>
        </Card>
      )}
    </div>
  )
}

function ChainView({
  data,
  selectedExpiry,
  onExpiry,
}: {
  data: OptionsChain
  selectedExpiry: string
  onExpiry: (e: string) => void
}) {
  const [showITM, setShowITM] = useState(false)

  const calls = showITM ? data.calls : data.calls.filter(c => !c.in_the_money).slice(0, 15)
  const puts  = showITM ? data.puts  : data.puts.filter(p => !p.in_the_money).slice(0, 15)

  return (
    <div className="space-y-4">
      {/* Metrics bar */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricCard label="Underlying" value={`$${data.underlying_price.toFixed(2)}`} />
        <MetricCard label="Max Pain" value={`$${data.max_pain.toFixed(2)}`} color="amber" />
        <MetricCard
          label="Put/Call Ratio"
          value={data.put_call_ratio.toFixed(3)}
          color={data.put_call_ratio < 0.7 ? 'green' : data.put_call_ratio > 1.0 ? 'red' : 'amber'}
          note={data.put_call_ratio < 0.7 ? 'Bullish' : data.put_call_ratio > 1.0 ? 'Bearish' : 'Neutral'}
        />
        <MetricCard label="Contracts" value={`${data.calls.length + data.puts.length}`} />
      </div>

      {/* Expiry selector */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-[var(--color-text-muted)]">Expiry:</span>
        {data.expiries.map(exp => (
          <button
            key={exp}
            onClick={() => onExpiry(exp)}
            className={cn(
              'rounded-full px-3 py-1 text-xs font-medium transition-colors',
              exp === selectedExpiry
                ? 'bg-[var(--color-accent-blue)] text-white'
                : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
            )}
          >
            {exp}
          </button>
        ))}
        <button
          onClick={() => setShowITM(v => !v)}
          className={cn(
            'ml-auto rounded-full px-3 py-1 text-xs font-medium transition-colors',
            showITM
              ? 'bg-purple-500/20 text-purple-400'
              : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)]'
          )}
        >
          {showITM ? 'All strikes' : 'OTM only'}
        </button>
      </div>

      {/* Chain tables side by side */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <ContractTable title="Calls" contracts={calls} kind="call" spot={data.underlying_price} />
        <ContractTable title="Puts"  contracts={puts}  kind="put"  spot={data.underlying_price} />
      </div>
    </div>
  )
}

function ContractTable({
  title,
  contracts,
  kind,
  spot,
}: {
  title: string
  contracts: OptionContract[]
  kind: 'call' | 'put'
  spot: number
}) {
  return (
    <Card className="p-0 overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--color-border)] flex items-center justify-between">
        <span className={cn(
          'text-sm font-semibold',
          kind === 'call' ? 'text-green-400' : 'text-red-400'
        )}>
          {title}
        </span>
        <span className="text-xs text-[var(--color-text-muted)]">Spot ${spot.toFixed(2)}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[var(--color-border)]">
              {['Strike', 'Bid', 'Ask', 'Last', 'Vol', 'OI', 'IV%', 'Δ'].map(h => (
                <th key={h} className="px-3 py-2 text-left text-[var(--color-text-muted)] font-medium whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {contracts.map((c, i) => (
              <tr
                key={i}
                className={cn(
                  'border-b border-[var(--color-border)]/50 hover:bg-[var(--color-bg-elevated)] transition-colors',
                  c.in_the_money && 'bg-[var(--color-bg-elevated)]/60'
                )}
              >
                <td className="px-3 py-2 font-mono font-semibold text-[var(--color-text-primary)]">
                  {c.strike.toFixed(0)}
                  {c.in_the_money && (
                    <span className={cn(
                      'ml-1 text-[10px]',
                      kind === 'call' ? 'text-green-400' : 'text-red-400'
                    )}>ITM</span>
                  )}
                </td>
                <td className="px-3 py-2 font-mono text-[var(--color-text-secondary)]">{c.bid.toFixed(2)}</td>
                <td className="px-3 py-2 font-mono text-[var(--color-text-secondary)]">{c.ask.toFixed(2)}</td>
                <td className="px-3 py-2 font-mono text-[var(--color-text-primary)]">{c.last.toFixed(2)}</td>
                <td className="px-3 py-2 font-mono text-[var(--color-text-muted)]">{fmtNum(c.volume)}</td>
                <td className="px-3 py-2 font-mono text-[var(--color-text-muted)]">{fmtNum(c.open_interest)}</td>
                <td className={cn(
                  'px-3 py-2 font-mono',
                  c.implied_volatility > 60 ? 'text-red-400' : c.implied_volatility > 35 ? 'text-amber-400' : 'text-green-400'
                )}>
                  {c.implied_volatility.toFixed(1)}%
                </td>
                <td className="px-3 py-2 font-mono text-[var(--color-text-secondary)]">
                  {c.delta != null ? c.delta.toFixed(3) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

function MetricCard({
  label,
  value,
  color,
  note,
}: {
  label: string
  value: string
  color?: 'green' | 'red' | 'amber'
  note?: string
}) {
  return (
    <Card className="text-center py-3">
      <p className="text-xs text-[var(--color-text-muted)] mb-1">{label}</p>
      <p className={cn(
        'text-lg font-bold font-mono',
        color === 'green' && 'text-green-400',
        color === 'red'   && 'text-red-400',
        color === 'amber' && 'text-amber-400',
        !color            && 'text-[var(--color-text-primary)]',
      )}>
        {value}
      </p>
      {note && <p className={cn(
        'text-xs mt-0.5',
        color === 'green' && 'text-green-400',
        color === 'red'   && 'text-red-400',
        color === 'amber' && 'text-amber-400',
      )}>{note}</p>}
    </Card>
  )
}

function fmtNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`
  return String(n)
}
