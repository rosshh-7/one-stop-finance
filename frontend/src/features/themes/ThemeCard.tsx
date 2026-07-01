import { TrendingUp, TrendingDown, Minus, Users, DollarSign, Shield, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import type { Theme } from './api'

interface ThemeCardProps {
  theme: Theme
  onClick: (theme: Theme) => void
}

const LIFECYCLE_CONFIG: Record<string, { label: string; variant: 'green' | 'blue' | 'amber' | 'red' | 'cyan' | 'default' }> = {
  EMERGING: { label: 'Emerging',  variant: 'cyan'    },
  BUILDING: { label: 'Building',  variant: 'blue'    },
  PEAK:     { label: 'Peak',      variant: 'green'   },
  FADING:   { label: 'Fading',    variant: 'amber'   },
  COOLING:  { label: 'Cooling',   variant: 'red'     },
  STABLE:   { label: 'Stable',    variant: 'default' },
}

const LEVEL_RING: Record<string, string> = {
  alert: 'ring-2 ring-green-500/40',
  watch: 'ring-2 ring-amber-500/30',
  quiet: '',
}

function ScoreArc({ score }: { score: number }) {
  const r = 28
  const circ = 2 * Math.PI * r
  const filled = (score / 100) * circ
  const color = score >= 70 ? '#22c55e' : score >= 45 ? '#f59e0b' : '#6b7280'

  return (
    <div className="relative flex items-center justify-center w-16 h-16">
      <svg width={64} height={64} className="-rotate-90">
        <circle cx={32} cy={32} r={r} stroke="var(--color-border)" strokeWidth={5} fill="none" />
        <circle
          cx={32} cy={32} r={r}
          stroke={color} strokeWidth={5} fill="none"
          strokeDasharray={`${filled} ${circ - filled}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      </svg>
      <span className="absolute text-sm font-bold text-[var(--color-text-primary)]">
        {Math.round(score)}
      </span>
    </div>
  )
}

function VelocityBadge({ velocity }: { velocity: number | null }) {
  if (velocity === null || velocity === undefined) return null
  const abs = Math.abs(velocity)
  if (abs < 1) return <Minus className="h-3 w-3 text-[var(--color-text-secondary)]" />
  if (velocity > 0)
    return (
      <span className="flex items-center gap-0.5 text-xs text-green-400 font-medium">
        <TrendingUp className="h-3 w-3" />+{abs.toFixed(0)}
      </span>
    )
  return (
    <span className="flex items-center gap-0.5 text-xs text-red-400 font-medium">
      <TrendingDown className="h-3 w-3" />{velocity.toFixed(0)}
    </span>
  )
}

export function ThemeCard({ theme, onClick }: ThemeCardProps) {
  const s = theme.score
  const score = s?.score ?? 0
  const lifecycle = s?.lifecycle_stage ?? 'STABLE'
  const lc = LIFECYCLE_CONFIG[lifecycle] ?? LIFECYCLE_CONFIG.STABLE

  return (
    <button
      onClick={() => onClick(theme)}
      className={cn(
        'w-full text-left rounded-xl p-4 bg-[var(--color-bg-elevated)] border border-[var(--color-border)]',
        'hover:border-[var(--color-accent-blue)]/40 transition-all duration-200',
        LEVEL_RING[s?.level ?? 'quiet'],
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{theme.name}</p>
          <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">{theme.category}</p>
        </div>
        <Badge variant={lc.variant} className="shrink-0">{lc.label}</Badge>
      </div>

      {/* Score + velocity */}
      <div className="flex items-center gap-3 mb-3">
        <ScoreArc score={score} />
        <div className="space-y-1">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-[var(--color-text-secondary)]">Score</span>
            <VelocityBadge velocity={s?.velocity ?? null} />
          </div>
          {theme.benchmark_etf && (
            <span className="text-xs font-mono text-[var(--color-text-secondary)]">
              ETF: {theme.benchmark_etf}
            </span>
          )}
        </div>
      </div>

      {/* Signal pills */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {(s?.unique_companies_buying ?? 0) > 0 && (
          <span className="flex items-center gap-1 text-xs bg-green-500/10 text-green-400 px-2 py-0.5 rounded-full">
            <Users className="h-2.5 w-2.5" />
            {s!.unique_companies_buying} buying
          </span>
        )}
        {(s?.total_value_accumulated ?? 0) > 0 && (
          <span className="flex items-center gap-1 text-xs bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full">
            <DollarSign className="h-2.5 w-2.5" />
            ${((s!.total_value_accumulated) / 1_000_000).toFixed(1)}M
          </span>
        )}
        {s?.congress_signal && (
          <span className="flex items-center gap-1 text-xs bg-purple-500/10 text-purple-400 px-2 py-0.5 rounded-full">
            <Shield className="h-2.5 w-2.5" />
            Congress
          </span>
        )}
        {(s?.contracts_count ?? 0) > 0 && (
          <span className="flex items-center gap-1 text-xs bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded-full">
            <FileText className="h-2.5 w-2.5" />
            {s!.contracts_count} contracts
          </span>
        )}
        {(s?.unique_companies_selling ?? 0) >= 2 && (
          <span className="flex items-center gap-1 text-xs bg-red-500/10 text-red-400 px-2 py-0.5 rounded-full">
            {s!.unique_companies_selling} selling
          </span>
        )}
      </div>

      {/* Top tickers */}
      {theme.top_tickers.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {theme.top_tickers.slice(0, 4).map((sym) => (
            <span key={sym} className="text-xs font-mono bg-[var(--color-bg-base)] px-1.5 py-0.5 rounded text-[var(--color-text-secondary)]">
              {sym}
            </span>
          ))}
        </div>
      )}
    </button>
  )
}
