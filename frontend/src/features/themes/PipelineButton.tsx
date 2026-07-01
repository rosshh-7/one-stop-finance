import { Play, CheckCircle, AlertCircle, Loader2, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { usePipelineStatus, useTriggerPipeline } from './api'

function timeAgo(iso: string | null): string {
  if (!iso) return 'Never'
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60_000)
  if (m < 1) return 'Just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export function PipelineButton() {
  const { data } = usePipelineStatus()
  const { mutate: run, isPending } = useTriggerPipeline()

  const status   = data?.status ?? 'idle'
  const isRunning = status === 'running' || isPending
  const stepLabel = data?.step_label || data?.current_step || ''

  return (
    <div className="flex items-center gap-3">
      {/* Status indicator */}
      <div className="hidden sm:flex items-center gap-1.5 text-xs text-[var(--color-text-secondary)]">
        {status === 'done' && (
          <>
            <CheckCircle className="h-3.5 w-3.5 text-green-400" />
            <span>Updated {timeAgo(data?.last_run ?? null)}</span>
          </>
        )}
        {status === 'running' && (
          <>
            <Loader2 className="h-3.5 w-3.5 text-blue-400 animate-spin" />
            <span className="text-blue-400">{stepLabel || 'Running...'}</span>
          </>
        )}
        {status === 'error' && (
          <>
            <AlertCircle className="h-3.5 w-3.5 text-red-400" />
            <span className="text-red-400">Failed — retry?</span>
          </>
        )}
        {status === 'idle' && data?.last_run && (
          <>
            <Clock className="h-3.5 w-3.5" />
            <span>Last run {timeAgo(data.last_run)}</span>
          </>
        )}
        {status === 'idle' && !data?.last_run && (
          <span>Pipeline not yet run</span>
        )}
      </div>

      {/* Run button */}
      <Button
        variant="primary"
        size="sm"
        loading={isRunning}
        disabled={isRunning}
        onClick={() => run()}
      >
        {!isRunning && <Play className="h-3.5 w-3.5" />}
        {isRunning ? (stepLabel || 'Running...') : 'Run Pipeline'}
      </Button>
    </div>
  )
}
