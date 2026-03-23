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
import { Plus, Trash2, Shield } from 'lucide-react'

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
    <PageLayout
      title="Approval Policies"
      description="Configure review chain and quorum workflows"
      actions={
        <button onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-[13px] font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 cursor-pointer transition-colors">
          <Plus size={14} /> New Policy
        </button>
      }
    >
      {isLoading ? <PageSkeleton /> : (
        <div className="max-w-4xl space-y-4">
          {showForm && (
            <div className="rounded-lg border border-border bg-card p-5">
              <h3 className="text-sm font-semibold text-foreground mb-3">Create Policy</h3>
              <PolicyForm
                onSubmit={(data) => createMutation.mutate(data)}
                onCancel={() => setShowForm(false)}
                isLoading={createMutation.isPending}
              />
              {createMutation.isError && (
                <p className="text-[12px] text-red-600 dark:text-red-400 mt-2">{(createMutation.error as Error).message}</p>
              )}
            </div>
          )}

          {policies && policies.length > 0 ? (
            <div className="rounded-lg border border-border bg-card divide-y divide-border/50">
              {policies.map((policy) => (
                <div key={policy.id} className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-foreground">{policy.name}</span>
                    <StatusBadge status={policy.policy_type === 'chain' ? 'processing' : 'pending_review'} />
                    <span className="text-[12px] text-muted-foreground capitalize">{policy.policy_type}</span>
                    {policy.deadline_hours && (
                      <span className="text-[12px] text-muted-foreground tabular-nums">{policy.deadline_hours}h deadline</span>
                    )}
                  </div>
                  <button onClick={() => deleteMutation.mutate(policy.id)}
                    disabled={deleteMutation.isPending}
                    className="text-muted-foreground hover:text-red-600 transition-colors cursor-pointer">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          ) : !showForm && (
            <div className="rounded-lg border border-border bg-card py-12 text-center text-muted-foreground">
              <div className="flex flex-col items-center gap-2">
                <Shield size={24} className="text-muted-foreground/40" />
                <p className="text-[13px]">No approval policies yet.</p>
              </div>
            </div>
          )}
        </div>
      )}
    </PageLayout>
  )
}
