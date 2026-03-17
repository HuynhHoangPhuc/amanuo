/** Batch table review — spreadsheet-like view for reviewing multiple documents. */

import { useState, useCallback } from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { BatchResponse, JobListResponse } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { StatusBadge } from '#/components/status-badge'
import { PageSkeleton } from '#/components/loading-skeleton'
import { ArrowLeft, Check, CheckCheck } from 'lucide-react'

export const Route = createFileRoute('/batches_/$batchId/review')({ component: BatchReviewPage })

function BatchReviewPage() {
  const { batchId } = Route.useParams()
  const queryClient = useQueryClient()

  const { data: _batch } = useQuery({
    queryKey: queryKeys.batches.detail(batchId),
    queryFn: () => api.get<BatchResponse>(`/batches/${batchId}`),
  })

  // Fetch jobs in this batch that need review
  const { data: jobsData, isLoading } = useQuery({
    queryKey: ['batch-review', batchId],
    queryFn: () => api.get<JobListResponse>(`/jobs?status=pending_review&limit=100`),
  })

  const [editedCells, setEditedCells] = useState<Record<string, Record<string, string>>>({})

  const approveMutation = useMutation({
    mutationFn: (jobId: string) => api.post(`/reviews/${jobId}`, { status: 'approved' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all() })
      queryClient.invalidateQueries({ queryKey: ['batch-review', batchId] })
    },
  })

  const handleCellEdit = useCallback((jobId: string, field: string, value: string) => {
    setEditedCells((prev) => ({
      ...prev,
      [jobId]: { ...(prev[jobId] || {}), [field]: value },
    }))
  }, [])

  const handleRowApprove = (jobId: string) => {
    const edits = editedCells[jobId]
    if (edits && Object.keys(edits).length > 0) {
      // Submit with corrections
      const job = jobsData?.jobs.find((j) => j.id === jobId)
      const corrected = job?.result?.map((f) => ({
        label_name: f.label,
        value: edits[f.label] ?? f.value,
        confidence: f.confidence,
      }))
      api.post(`/reviews/${jobId}`, { status: 'corrected', corrected_result: corrected }).then(() => {
        queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all() })
        queryClient.invalidateQueries({ queryKey: ['batch-review', batchId] })
      })
    } else {
      approveMutation.mutate(jobId)
    }
  }

  const handleBulkApprove = () => {
    jobsData?.jobs.forEach((job) => {
      if (!editedCells[job.id] || Object.keys(editedCells[job.id]).length === 0) {
        approveMutation.mutate(job.id)
      }
    })
  }

  // Collect all unique field labels across jobs
  const fieldLabels = Array.from(
    new Set(jobsData?.jobs.flatMap((j) => j.result?.map((r) => r.label) ?? []) ?? []),
  )

  return (
    <PageLayout
      title="Batch Review"
      actions={
        <div className="flex items-center gap-3">
          <Link to="/batches" className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft size={14} /> Back
          </Link>
          <button
            onClick={handleBulkApprove}
            className="flex items-center gap-2 rounded-lg bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700"
          >
            <CheckCheck size={14} /> Approve All Unchanged
          </button>
        </div>
      }
    >
      {isLoading ? (
        <PageSkeleton />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted">
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Job</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Status</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Conf</th>
                {fieldLabels.map((label) => (
                  <th key={label} className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">
                    {label}
                  </th>
                ))}
                <th className="px-3 py-2 text-center text-xs font-medium text-muted-foreground">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {jobsData?.jobs.map((job) => {
                const resultMap = Object.fromEntries(
                  job.result?.map((r) => [r.label, r]) ?? [],
                )
                return (
                  <tr key={job.id} className="hover:bg-muted">
                    <td className="px-3 py-2">
                      <Link
                        to="/reviews/$jobId"
                        params={{ jobId: job.id }}
                        className="font-mono text-xs text-primary hover:underline"
                      >
                        {job.id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {job.confidence != null ? `${Math.round(job.confidence * 100)}%` : '-'}
                    </td>
                    {fieldLabels.map((label) => {
                      const field = resultMap[label]
                      const editedValue = editedCells[job.id]?.[label]
                      return (
                        <td key={label} className="px-1 py-1">
                          <input
                            type="text"
                            value={editedValue ?? String(field?.value ?? '')}
                            onChange={(e) => handleCellEdit(job.id, label, e.target.value)}
                            className={`w-full rounded border px-2 py-1 text-xs ${
                              field && field.confidence < 0.85
                                ? 'border-yellow-300 bg-yellow-500/10'
                                : 'border-border'
                            } ${editedValue !== undefined ? 'ring-1 ring-primary/30' : ''}`}
                          />
                        </td>
                      )
                    })}
                    <td className="px-3 py-2 text-center">
                      <button
                        onClick={() => handleRowApprove(job.id)}
                        className="rounded bg-green-500/15 p-1.5 text-green-700 hover:bg-green-200"
                        title="Approve row"
                      >
                        <Check size={14} />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {(!jobsData?.jobs || jobsData.jobs.length === 0) && (
            <p className="py-8 text-center text-sm text-muted-foreground/70">No jobs pending review in this batch.</p>
          )}
        </div>
      )}
    </PageLayout>
  )
}
