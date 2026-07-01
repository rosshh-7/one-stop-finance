import { useState } from 'react'
import { Flame, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { SyncPanel } from '@/features/themes/SyncPanel'
import { ThemeCard } from '@/features/themes/ThemeCard'
import { TrendingPanel } from '@/features/themes/TrendingPanel'
import { ThemeDetailDrawer } from '@/features/themes/ThemeDetailDrawer'
import { SignalFeed } from '@/features/themes/SignalFeed'
import { PipelineButton } from '@/features/themes/PipelineButton'
import { useThemes, type Theme } from '@/features/themes/api'

const CATEGORY_TABS = ['All', 'Technology', 'Healthcare', 'Energy', 'Industrials', 'Financials', 'Materials', 'Utilities', 'Consumer']

export function ThemesPage() {
  const [selectedTheme, setSelectedTheme] = useState<Theme | null>(null)
  const [categoryFilter, setCategoryFilter] = useState('All')
  const { data, isLoading, refetch, isFetching } = useThemes()

  const themes = data?.themes ?? []
  const lastScored = data?.last_scored_at
    ? new Date(data.last_scored_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null

  const filtered = categoryFilter === 'All'
    ? themes
    : themes.filter((t) => t.category === categoryFilter)

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Flame className="h-6 w-6 text-amber-400" />
          <div>
            <h2 className="text-xl font-bold text-[var(--color-text-primary)]">Theme Intelligence</h2>
            <p className="text-sm text-[var(--color-text-secondary)]">
              Smart money convergence across 25 market themes
              {lastScored && <span className="ml-2 text-xs">· scored {lastScored}</span>}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" loading={isFetching} onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <PipelineButton />
        </div>
      </div>

      {/* Trending + Cooling panels */}
      <TrendingPanel onThemeClick={setSelectedTheme} />

      {/* Category filter tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {CATEGORY_TABS.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            className={`shrink-0 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              categoryFilter === cat
                ? 'bg-[var(--color-accent-blue)] text-white'
                : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Theme grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-48 rounded-xl bg-[var(--color-bg-elevated)] animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <Flame className="h-10 w-10 text-[var(--color-text-secondary)] mx-auto mb-3 opacity-40" />
          <p className="text-[var(--color-text-secondary)]">
            {themes.length === 0
              ? 'No themes scored yet — run the seed script and wait for the next scoring cycle'
              : `No themes in "${categoryFilter}"`
            }
          </p>
          {themes.length === 0 && (
            <p className="text-xs text-[var(--color-text-secondary)] mt-2">
              <code className="bg-[var(--color-bg-elevated)] px-2 py-0.5 rounded">python -m scripts.seed_themes</code>
            </p>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((theme) => (
            <ThemeCard key={theme.id} theme={theme} onClick={setSelectedTheme} />
          ))}
        </div>
      )}

      {/* Signal feed */}
      <SignalFeed />

      {/* Data source sync panel */}
      <SyncPanel />

      {/* Theme detail drawer */}
      <ThemeDetailDrawer
        theme={selectedTheme}
        onClose={() => setSelectedTheme(null)}
      />
    </div>
  )
}
