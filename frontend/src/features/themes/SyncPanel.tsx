import { RefreshCw, Database, TrendingUp, BarChart2, Layers, Activity } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth.store'
import { useSyncStatus, useTriggerSync, type SyncSource, type SyncSourceKey } from './api'

const SOURCE_ICONS: Record<SyncSourceKey, React.ReactNode> = {
  fmp:         <Database className="h-4 w-4" />,
  trends:      <TrendingUp className="h-4 w-4" />,
  polygon:     <BarChart2 className="h-4 w-4" />,
  etf:         <Layers className="h-4 w-4" />,
  etf_signals: <Activity className="h-4 w-4" />,
}

function staleBadge(source: SyncSource) {
  if (source.status === 'running')
    return <Badge variant="blue">Syncing...</Badge>
  if (source.status === 'error')
    return <Badge variant="red">Error</Badge>
  if (!source.last_synced_at)
    return <Badge variant="red">Never synced</Badge>
  if (source.is_stale)
    return <Badge variant="amber">Stale</Badge>
  return <Badge variant="green">Fresh</Badge>
}

function formatLastSynced(ts: string | null): string {
  if (!ts) return 'Never'
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function SyncPanel() {
  const { isAuthenticated } = useAuthStore()
  const { syncStatus, isLoading } = useSyncStatus()
  const { mutate: triggerSync, isPending } = useTriggerSync()

  // Sync controls are admin-only — hide for unauthenticated visitors
  if (!isAuthenticated) return null

  const anyRunning = syncStatus?.sources.some((s) => s.status === 'running') ?? false

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Data Sources</CardTitle>
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
              Rate-limited sources — sync manually or wait for the scheduled run
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            loading={isPending || anyRunning}
            onClick={() => triggerSync('all')}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Sync All
          </Button>
        </div>
      </CardHeader>

      <div className="divide-y divide-[var(--color-border)]">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="px-4 py-3 animate-pulse">
                <div className="h-4 bg-[var(--color-bg-elevated)] rounded w-40 mb-1" />
                <div className="h-3 bg-[var(--color-bg-elevated)] rounded w-64" />
              </div>
            ))
          : syncStatus?.sources.map((source) => (
              <div
                key={source.source}
                className="flex items-center justify-between px-4 py-3 gap-4"
              >
                <div className="flex items-start gap-3 min-w-0">
                  <span className="mt-0.5 text-[var(--color-text-secondary)] shrink-0">
                    {SOURCE_ICONS[source.source]}
                  </span>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-[var(--color-text-primary)]">
                        {source.label}
                      </span>
                      {staleBadge(source)}
                    </div>
                    <p className="text-xs text-[var(--color-text-secondary)] truncate">
                      {source.description}
                    </p>
                    {source.status === 'error' && source.error && (
                      <p className="text-xs text-red-400 mt-0.5 truncate">{source.error}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-xs text-[var(--color-text-secondary)] hidden sm:block">
                    {formatLastSynced(source.last_synced_at)}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    loading={source.status === 'running'}
                    disabled={source.status === 'running' || isPending}
                    onClick={() => triggerSync(source.source)}
                  >
                    <RefreshCw className="h-3 w-3" />
                    Sync
                  </Button>
                </div>
              </div>
            ))}
      </div>
    </Card>
  )
}
