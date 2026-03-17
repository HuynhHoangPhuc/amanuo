/** Side-by-side review page — document viewer + editable extraction fields. */

import { useState, useCallback, useEffect, useRef } from 'react'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { JobResponse, ExtractionResult } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { DocumentViewer } from '#/components/document-viewer'
import { FieldEditor } from '#/components/field-editor'
import { ReviewToolbar } from '#/components/review-toolbar'
import { PageSkeleton } from '#/components/loading-skeleton'
import { ArrowLeft } from 'lucide-react'

export const Route = createFileRoute('/reviews_/$jobId')({ component: ReviewDetailPage })

function ReviewDetailPage() {
  const { jobId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const startTime = useRef(Date.now())

  const { data: job, isLoading } = useQuery({
    queryKey: queryKeys.jobs.detail(jobId),
    queryFn: () => api.get<JobResponse>(`/jobs/${jobId}`),
  })

  const [editedFields, setEditedFields] = useState<ExtractionResult[]>([])
  const [modifiedFields, setModifiedFields] = useState<Set<string>>(new Set())

  // Initialize edited fields from job data
  useEffect(() => {
    if (job?.result) {
      setEditedFields(job.result.map((f) => ({ ...f })))
    }
  }, [job?.result])

  const handleFieldsChange = useCallback(
    (updated: ExtractionResult[]) => {
      setEditedFields(updated)
      // Track which fields changed
      if (job?.result) {
        const modified = new Set<string>()
        for (let i = 0; i < updated.length; i++) {
          if (String(updated[i].value) !== String(job.result[i]?.value)) {
            modified.add(updated[i].label)
          }
        }
        setModifiedFields(modified)
      }
    },
    [job?.result],
  )

  const submitMutation = useMutation({
    mutationFn: (body: { status: string; corrected_result?: Record<string, unknown>[] }) =>
      api.post(`/reviews/${jobId}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all() })
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all() })
      navigate({ to: '/reviews' })
    },
  })

  const reviewTimeMs = () => Date.now() - startTime.current

  const handleApprove = () => {
    submitMutation.mutate({ status: 'approved', review_time_ms: reviewTimeMs() } as any)
  }

  const handleCorrect = () => {
    const corrected = editedFields.map((f) => ({
      label_name: f.label,
      value: f.value,
      confidence: f.confidence,
    }))
    submitMutation.mutate({
      status: 'corrected',
      corrected_result: corrected,
      review_time_ms: reviewTimeMs(),
    } as any)
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !e.ctrlKey && !e.metaKey && e.target === document.body) {
        e.preventDefault()
        handleApprove()
      }
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && modifiedFields.size > 0) {
        e.preventDefault()
        handleCorrect()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [modifiedFields.size, editedFields])

  const documentUrl = `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}/jobs/${jobId}/document`

  return (
    <PageLayout
      title="Review Extraction"
      actions={
        <Link to="/reviews" className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft size={14} /> Back to Queue
        </Link>
      }
    >
      {isLoading ? (
        <PageSkeleton />
      ) : job ? (
        <div className="flex flex-col h-[calc(100vh-12rem)]">
          {/* Side-by-side panels */}
          <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
            {/* Left: document viewer */}
            <div className="rounded-xl border border-border bg-card overflow-hidden flex flex-col">
              <DocumentViewer src={documentUrl} alt={`Document for job ${jobId}`} />
            </div>

            {/* Right: editable fields */}
            <div className="rounded-xl border border-border bg-card overflow-auto p-5">
              <h2 className="text-sm font-semibold text-foreground mb-4">
                Extraction Results
                {job.confidence != null && (
                  <span className="ml-2 text-xs font-normal text-muted-foreground/70">
                    Overall: {Math.round(job.confidence * 100)}%
                  </span>
                )}
              </h2>
              {editedFields.length > 0 ? (
                <FieldEditor
                  fields={editedFields}
                  onChange={handleFieldsChange}
                  modifiedFields={modifiedFields}
                />
              ) : (
                <p className="text-sm text-muted-foreground/70">No extraction results.</p>
              )}
            </div>
          </div>

          {/* Bottom toolbar */}
          <ReviewToolbar
            onApprove={handleApprove}
            onCorrect={handleCorrect}
            hasChanges={modifiedFields.size > 0}
            isSubmitting={submitMutation.isPending}
          />
        </div>
      ) : (
        <p className="text-muted-foreground">Job not found.</p>
      )}
    </PageLayout>
  )
}
