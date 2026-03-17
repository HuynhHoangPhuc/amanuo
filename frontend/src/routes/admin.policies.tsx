/** Approval policy management page (admin only). */

import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { ApprovalPolicy } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { PolicyForm, type PolicyFormData } from '#/components/policy-form'
import { PageSkeleton } from '#/components/loading-skeleton'
import { StatusBadge } from '#/components/status-badge'
import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'

export const Route = createFileRoute('/admin/policies')({ component: AdminPoliciesPage })

function AdminPoliciesPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)

  const { data: policies, isLoading } = useQuery({
    queryKey: queryKeys.approvalPolicies.list(),
    queryFn: () => api.get<ApprovalPolicy[]>('/approval-policies'),
  })

  const createMutation = useMutation({
    mutationFn: (data: PolicyFormData) => api.post('/approval-policies', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.approvalPolicies.all() })
      setShowForm(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/approval-policies/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.approvalPolicies.all() })
    },
  })

  return (
    <PageLayout title="Approval Policies" actions={
      <button onClick={() => setShowForm(true)}
        className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
        <Plus size={14} /> New Policy
      </button>
    }>
      {isLoading ? <PageSkeleton /> : (
        <div className="max-w-4xl space-y-6">
          {showForm && (
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Create Policy</h3>
              <PolicyForm
                onSubmit={(data) => createMutation.mutate(data)}
                onCancel={() => setShowForm(false)}
                isLoading={createMutation.isPending}
              />
              {createMutation.isError && (
                <p className="text-xs text-red-600 mt-2">{(createMutation.error as Error).message}</p>
              )}
            </div>
          )}

          {policies && policies.length > 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white divide-y divide-gray-100">
              {policies.map((policy) => (
                <div key={policy.id} className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-800">{policy.name}</span>
                    <StatusBadge status={policy.policy_type === 'chain' ? 'processing' : 'pending_review'} />
                    <span className="text-xs text-gray-400 capitalize">{policy.policy_type}</span>
                    {policy.deadline_hours && (
                      <span className="text-xs text-gray-400">{policy.deadline_hours}h deadline</span>
                    )}
                  </div>
                  <button onClick={() => deleteMutation.mutate(policy.id)}
                    disabled={deleteMutation.isPending}
                    className="text-gray-400 hover:text-red-600 transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          ) : !showForm && (
            <p className="text-sm text-gray-400 py-8 text-center">No approval policies yet.</p>
          )}
        </div>
      )}
    </PageLayout>
  )
}
