/** Role display badge — uses shadcn Badge with dark-safe colors. */

import { Badge } from '#/components/ui/badge'
import { cn } from '#/lib/utils'
import type { UserRole } from '#/lib/types'

const ROLE_STYLES: Record<UserRole, string> = {
  admin: 'bg-red-500/10 text-red-700 border-red-500/20 dark:text-red-400',
  approver: 'bg-orange-500/10 text-orange-700 border-orange-500/20 dark:text-orange-400',
  reviewer: 'bg-blue-500/10 text-blue-700 border-blue-500/20 dark:text-blue-400',
  member: 'bg-muted text-muted-foreground border-border',
  viewer: 'bg-muted text-muted-foreground border-border',
}

interface RoleBadgeProps {
  role: UserRole
  className?: string
}

export function RoleBadge({ role, className }: RoleBadgeProps) {
  const styles = ROLE_STYLES[role] ?? 'bg-muted text-muted-foreground border-border'
  return (
    <Badge variant="outline" className={cn('capitalize', styles, className)}>
      {role}
    </Badge>
  )
}
