/** User role management page (admin only). */

import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { UserResponse, UserRole } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { RoleBadge } from '#/components/role-badge'
import { PageSkeleton } from '#/components/loading-skeleton'
import { useState } from 'react'
import { Plus, X } from 'lucide-react'

export const Route = createFileRoute('/admin/users')({ component: AdminUsersPage })

const ALL_ROLES: UserRole[] = ['viewer', 'member', 'reviewer', 'approver', 'admin']

function AdminUsersPage() {
  const queryClient = useQueryClient()
  const [addingRole, setAddingRole] = useState<{ userId: string; role: UserRole } | null>(null)

  const { data: users, isLoading } = useQuery({
    queryKey: queryKeys.users.list(),
    queryFn: () => api.get<UserResponse[]>('/users'),
  })

  const assignMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.post(`/users/${userId}/roles`, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all() })
      setAddingRole(null)
    },
  })

  const removeMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.delete(`/users/${userId}/roles/${role}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all() })
    },
  })

  return (
    <PageLayout title="User Management">
      {isLoading ? <PageSkeleton /> : (
        <div className="max-w-4xl">
          {users && users.length > 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white divide-y divide-gray-100">
              {users.map((user) => (
                <div key={user.id} className="px-4 py-3">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="text-sm font-medium text-gray-800">{user.email}</span>
                      {user.display_name && (
                        <span className="text-xs text-gray-400 ml-2">{user.display_name}</span>
                      )}
                    </div>
                    <span className="text-xs text-gray-400">{new Date(user.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {user.roles.map((role) => (
                      <div key={role} className="flex items-center gap-0.5">
                        <RoleBadge role={role} />
                        <button
                          onClick={() => removeMutation.mutate({ userId: user.id, role })}
                          disabled={removeMutation.isPending}
                          className="text-gray-300 hover:text-red-500 transition-colors"
                          title={`Remove ${role} role`}
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))}
                    {/* Add role dropdown */}
                    {addingRole?.userId === user.id ? (
                      <select
                        value=""
                        onChange={(e) => {
                          if (e.target.value) {
                            assignMutation.mutate({ userId: user.id, role: e.target.value })
                          }
                        }}
                        className="text-xs border border-gray-300 rounded px-1 py-0.5"
                        autoFocus
                        onBlur={() => setAddingRole(null)}
                      >
                        <option value="">Select role...</option>
                        {ALL_ROLES.filter((r) => !user.roles.includes(r)).map((r) => (
                          <option key={r} value={r}>{r}</option>
                        ))}
                      </select>
                    ) : (
                      <button
                        onClick={() => setAddingRole({ userId: user.id, role: 'member' })}
                        className="text-gray-300 hover:text-blue-500 transition-colors"
                        title="Add role"
                      >
                        <Plus size={14} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 py-8 text-center">No users found.</p>
          )}
        </div>
      )}
    </PageLayout>
  )
}
