/** Status indicator — dot + text, Linear-style. */

import { cn } from '#/lib/utils'
import type { BatchStatus, JobStatus } from '#/lib/types'

type Status = JobStatus | BatchStatus | 'success' | 'failed' | 'pending' | 'partial' | 'active' | 'inactive'

const STATUS_DOT_COLORS: Record<string, string> = {
  pending: 'bg-yellow-500',
  processing: 'bg-blue-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  pending_review: 'bg-purple-500',
  reviewed: 'bg-teal-500',
  partial: 'bg-orange-500',
  success: 'bg-green-500',
  active: 'bg-green-500',
  inactive: 'bg-zinc-400',
}

interface StatusBadgeProps {
  status: Status
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const dotColor = STATUS_DOT_COLORS[status] ?? 'bg-zinc-400'
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-[13px] text-muted-foreground', className)}>
      <span className={cn('h-2 w-2 rounded-full', dotColor)} />
      <span className="capitalize">{status.replaceAll('_', ' ')}</span>
    </span>
  )
}
