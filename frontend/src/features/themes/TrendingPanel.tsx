import { TrendingUp, AlertTriangle } from 'lucide-react'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useTrendingThemes, useCoolingThemes, type Theme } from './api'

function MiniRow({ theme, onClick }: { theme: Theme; onClick: (t: Theme) => void }) {
  const s = theme.score
  const vel = s?.velocity ?? 0
  return (
    <button
      onClick={() => onClick(theme)}
      className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-[var(--color-bg-elevated)] transition-colors rounded-lg"
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <div className={`w-2 h-2 rounded-full shrink-0 ${
          (s?.level === 'alert') ? 'bg-green-400' :
          (s?.level === 'watch') ? 'bg-amber-400' : 'bg-gray-500'
        }`} />
        <span className="text-sm text-[var(--color-text-primary)] truncate">{theme.name}</span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs font-bold text-[var(--color-text-primary)]">
          {Math.round(s?.score ?? 0)}
        </span>
        {vel !== 0 && (
          <span className={`text-xs font-medium ${vel > 0 ? 'text-green-400' : 'text-red-400'}`}>
            {vel > 0 ? '+' : ''}{vel.toFixed(0)}
          </span>
        )}
      </div>
    </button>
  )
}

interface TrendingPanelProps {
  onThemeClick: (theme: Theme) => void
}

export function TrendingPanel({ onThemeClick }: TrendingPanelProps) {
  const { data: trending, isLoading: tLoading } = useTrendingThemes()
  const { data: cooling } = useCoolingThemes()

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {/* Trending */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-green-400" />
            <CardTitle>Building Momentum</CardTitle>
          </div>
          <p className="text-xs text-[var(--color-text-secondary)]">Highest velocity this week</p>
        </CardHeader>
        <div className="pb-2">
          {tLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="px-4 py-2.5 animate-pulse">
                  <div className="h-3.5 bg-[var(--color-bg-elevated)] rounded w-3/4" />
                </div>
              ))
            : (trending ?? []).length === 0
            ? <p className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">No themes building momentum yet</p>
            : trending!.map((t) => <MiniRow key={t.id} theme={t} onClick={onThemeClick} />)
          }
        </div>
      </Card>

      {/* Cooling */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-400" />
            <CardTitle>Cooling Alerts</CardTitle>
          </div>
          <p className="text-xs text-[var(--color-text-secondary)]">Insider selling clusters detected</p>
        </CardHeader>
        <div className="pb-2">
          {(cooling ?? []).length === 0
            ? <p className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">No cooling signals detected</p>
            : cooling!.map((t) => (
                <button
                  key={t.id}
                  onClick={() => onThemeClick(t)}
                  className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-[var(--color-bg-elevated)] transition-colors rounded-lg"
                >
                  <span className="text-sm text-red-400 truncate">{t.name}</span>
                  <Badge variant="red">Cooling</Badge>
                </button>
              ))
          }
        </div>
      </Card>
    </div>
  )
}
