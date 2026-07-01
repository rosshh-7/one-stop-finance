import { useState } from 'react'
import { ArrowUpCircle, ArrowDownCircle, Shield, FileText } from 'lucide-react'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useInsiderFeed, useCongressFeed, useContractFeed } from './api'

type FeedTab = 'insider' | 'congress' | 'contracts'

function formatUSD(v: number | null): string {
  if (!v) return '—'
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const h = Math.floor(diff / 3_600_000)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export function SignalFeed() {
  const [tab, setTab] = useState<FeedTab>('insider')
  const { data: insider, isLoading: iLoad } = useInsiderFeed()
  const { data: congress } = useCongressFeed()
  const { data: contracts } = useContractFeed()

  const tabs: { key: FeedTab; label: string }[] = [
    { key: 'insider',   label: 'Insider'    },
    { key: 'congress',  label: 'Congress'   },
    { key: 'contracts', label: 'Contracts'  },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Signal Feed</CardTitle>
        <div className="flex gap-1 mt-2">
          {tabs.map((t) => (
            <Button
              key={t.key}
              variant={tab === t.key ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </Button>
          ))}
        </div>
      </CardHeader>

      <div className="divide-y divide-[var(--color-border)] max-h-80 overflow-y-auto">
        {tab === 'insider' && (
          iLoad
            ? Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="px-4 py-3 animate-pulse">
                  <div className="h-4 bg-[var(--color-bg-elevated)] rounded w-1/2 mb-1" />
                  <div className="h-3 bg-[var(--color-bg-elevated)] rounded w-3/4" />
                </div>
              ))
            : (insider ?? []).map((sig, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3">
                  {sig.transaction_type === 'buy'
                    ? <ArrowUpCircle className="h-4 w-4 text-green-400 shrink-0" />
                    : <ArrowDownCircle className="h-4 w-4 text-red-400 shrink-0" />
                  }
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono font-bold text-[var(--color-text-primary)]">{sig.symbol}</span>
                      <span className="text-xs text-[var(--color-text-secondary)] truncate">{sig.insider_name}</span>
                      {sig.insider_title && (
                        <span className="text-xs text-[var(--color-text-secondary)] hidden sm:block truncate">· {sig.insider_title}</span>
                      )}
                    </div>
                    <span className="text-xs text-[var(--color-text-secondary)]">{timeAgo(sig.filing_date)}</span>
                  </div>
                  <span className={`text-sm font-medium shrink-0 ${sig.transaction_type === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                    {formatUSD(sig.total_value)}
                  </span>
                </div>
              ))
        )}

        {tab === 'congress' && (
          (congress ?? []).length === 0
            ? <p className="px-4 py-6 text-sm text-center text-[var(--color-text-secondary)]">No congressional trades in last 45 days</p>
            : (congress ?? []).map((sig, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3">
                  <Shield className="h-4 w-4 text-purple-400 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono font-bold text-[var(--color-text-primary)]">{sig.symbol}</span>
                      <span className="text-xs text-[var(--color-text-secondary)] truncate">{sig.insider_name}</span>
                    </div>
                    <span className="text-xs text-[var(--color-text-secondary)]">{timeAgo(sig.filing_date)}</span>
                  </div>
                  <span className="text-sm font-medium text-purple-400 shrink-0">{formatUSD(sig.total_value)}</span>
                </div>
              ))
        )}

        {tab === 'contracts' && (
          (contracts ?? []).length === 0
            ? <p className="px-4 py-6 text-sm text-center text-[var(--color-text-secondary)]">No contracts in last 30 days</p>
            : (contracts ?? []).map((c, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3">
                  <FileText className="h-4 w-4 text-amber-400 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-[var(--color-text-primary)] truncate">{c.recipient_name ?? '—'}</p>
                    <p className="text-xs text-[var(--color-text-secondary)] truncate">{c.agency_name}</p>
                  </div>
                  <span className="text-sm font-medium text-amber-400 shrink-0">{formatUSD(c.award_amount)}</span>
                </div>
              ))
        )}
      </div>
    </Card>
  )
}
