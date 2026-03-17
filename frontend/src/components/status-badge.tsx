/** Status badge for job/batch states — uses shadcn Badge with dark-safe colors. */

import { Badge } from '#/components/ui/badge'
import { cn } from '#/lib/utils'
import type { BatchStatus, JobStatus } from '#/lib/types'

type Status = JobStatus | BatchStatus | 'success' | 'failed' | 'pending' | 'partial' | 'active' | 'inactive'

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-500/10 text-yellow-700 border-yellow-500/20 dark:text-yellow-400',
  processing: 'bg-blue-500/10 text-blue-700 border-blue-500/20 dark:text-blue-400',
  completed: 'bg-green-500/10 text-green-700 border-green-500/20 dark:text-green-400',
  failed: 'bg-red-500/10 text-red-700 border-red-500/20 dark:text-red-400',
  pending_review: 'bg-purple-500/10 text-purple-700 border-purple-500/20 dark:text-purple-400',
  reviewed: 'bg-teal-500/10 text-teal-700 border-teal-500/20 dark:text-teal-400',
  partial: 'bg-orange-500/10 text-orange-700 border-orange-500/20 dark:text-orange-400',
  success: 'bg-green-500/10 text-green-700 border-green-500/20 dark:text-green-400',
  active: 'bg-green-500/10 text-green-700 border-green-500/20 dark:text-green-400',
  inactive: 'bg-muted text-muted-foreground border-border',
}

interface StatusBadgeProps {
  status: Status
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const styles = STATUS_STYLES[status] ?? 'bg-muted text-muted-foreground border-border'
  return (
    <Badge variant="outline" className={cn('capitalize', styles, className)}>
      {status}
    </Badge>
  )
}
