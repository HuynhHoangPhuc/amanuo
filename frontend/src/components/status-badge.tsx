/** Status indicator — pill badge with subtle bg tint. */

import { cn } from '#/lib/utils'
import type { BatchStatus, JobStatus } from '#/lib/types'

type Status = JobStatus | BatchStatus | 'success' | 'failed' | 'pending' | 'partial' | 'active' | 'inactive'

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  processing: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  completed: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  failed: 'bg-red-500/10 text-red-700 dark:text-red-400',
  pending_review: 'bg-purple-500/10 text-purple-700 dark:text-purple-400',
  reviewed: 'bg-teal-500/10 text-teal-700 dark:text-teal-400',
  partial: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
  success: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  active: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  inactive: 'bg-slate-500/10 text-slate-600 dark:text-slate-400',
}

const STATUS_DOT_COLORS: Record<string, string> = {
  pending: 'bg-amber-500',
  processing: 'bg-blue-500',
  completed: 'bg-emerald-500',
  failed: 'bg-red-500',
  pending_review: 'bg-purple-500',
  reviewed: 'bg-teal-500',
  partial: 'bg-orange-500',
  success: 'bg-emerald-500',
  active: 'bg-emerald-500',
  inactive: 'bg-slate-400',
}

interface StatusBadgeProps {
  status: Status
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const style = STATUS_STYLES[status] ?? 'bg-slate-500/10 text-slate-600 dark:text-slate-400'
  const dotColor = STATUS_DOT_COLORS[status] ?? 'bg-slate-400'
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[12px] font-medium', style, className)}>
      <span className={cn('h-1.5 w-1.5 rounded-full', dotColor)} />
      <span className="capitalize">{status.replaceAll('_', ' ')}</span>
    </span>
  )
}
