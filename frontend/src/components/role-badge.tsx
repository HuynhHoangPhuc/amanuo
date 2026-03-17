/** Role display badge with color coding per role. */

import type { UserRole } from '#/lib/types'

const ROLE_STYLES: Record<UserRole, string> = {
  admin: 'bg-red-50 text-red-700 border-red-200',
  approver: 'bg-orange-50 text-orange-700 border-orange-200',
  reviewer: 'bg-blue-50 text-blue-700 border-blue-200',
  member: 'bg-gray-50 text-gray-700 border-gray-200',
  viewer: 'bg-slate-50 text-slate-600 border-slate-200',
}

interface RoleBadgeProps {
  role: UserRole
  className?: string
}

export function RoleBadge({ role, className = '' }: RoleBadgeProps) {
  const styles = ROLE_STYLES[role] ?? 'bg-gray-100 text-gray-600 border-gray-200'
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${styles} ${className}`}
    >
      {role}
    </span>
  )
}
