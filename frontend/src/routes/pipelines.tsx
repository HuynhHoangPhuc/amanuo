/** Pipeline management: list, create with YAML editor, delete. */

import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { PipelineResponse, PipelineCreateRequest } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { TableRowSkeleton } from '#/components/loading-skeleton'
import { useToast } from '#/components/toast-provider'
import { Plus, Trash2, GitBranch, ChevronDown, ChevronRight } from 'lucide-react'

export const Route = createFileRoute('/pipelines')({ component: PipelinesPage })

const DEFAULT_YAML = `# Pipeline configuration
steps:
  - provider: local
    model: qwen3-vl:4b
    fallback: true
  - provider: gemini
    model: gemini-1.5-flash
`

function CreatePipelineForm({ onClose }: { onClose: () => void }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [config, setConfig] = useState(DEFAULT_YAML)

  const mutation = useMutation({
    mutationFn: (req: PipelineCreateRequest) =>
      api.post<PipelineResponse>('/pipelines', req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.pipelines.list() })
      toast('Pipeline created', 'success')
      onClose()
    },
    onError: (e: Error) => toast(e.message, 'error'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate({ name, description, config })
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-2xl rounded-lg border border-border bg-card shadow-lg p-6 space-y-4"
      >
        <h2 className="text-base font-semibold text-foreground">New Pipeline</h2>
        <input
          className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="Pipeline name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <div>
          <label className="block text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
            Config (YAML)
          </label>
          <textarea
            className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-[13px] font-mono focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            rows={10}
            value={config}
            onChange={(e) => setConfig(e.target.value)}
            spellCheck={false}
            required
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-md border border-border hover:bg-accent cursor-pointer transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="px-4 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 cursor-pointer transition-colors"
          >
            {mutation.isPending ? 'Creating...' : 'Create'}
          </button>
        </div>
      </form>
    </div>
  )
}

function PipelinesPage() {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)

  const { data: pipelines = [], isLoading } = useQuery({
    queryKey: queryKeys.pipelines.list(),
    queryFn: () => api.get<PipelineResponse[]>('/pipelines'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/pipelines/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.pipelines.list() })
      toast('Pipeline deleted', 'success')
    },
    onError: (e: Error) => toast(e.message, 'error'),
  })

  return (
    <PageLayout
      title="Pipelines"
      description="Configure extraction provider chains"
      actions={
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-[13px] font-medium text-primary-foreground hover:bg-primary/90 cursor-pointer transition-colors"
        >
          <Plus size={14} /> New Pipeline
        </button>
      }
    >
      {showForm && <CreatePipelineForm onClose={() => setShowForm(false)} />}
      <div className="space-y-3">
        {isLoading &&
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-border bg-card p-4">
              <TableRowSkeleton cols={1} />
            </div>
          ))}
        {!isLoading && pipelines.map((p) => (
          <div key={p.id} className="rounded-lg border border-border bg-card">
            <div
              className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-accent/50 transition-colors"
              onClick={() => setExpanded(expanded === p.id ? null : p.id)}
            >
              <div className="flex items-center gap-3">
                {expanded === p.id ? <ChevronDown size={14} className="text-muted-foreground" /> : <ChevronRight size={14} className="text-muted-foreground" />}
                <div>
                  <p className="font-medium text-foreground text-sm">{p.name}</p>
                  {p.description && (
                    <p className="text-[12px] text-muted-foreground mt-0.5">{p.description}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[12px] text-muted-foreground tabular-nums">
                  {new Date(p.updated_at).toLocaleDateString()}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(p.id) }}
                  className="text-red-400 hover:text-red-600 p-1 cursor-pointer transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
            {expanded === p.id && (
              <div className="border-t border-border px-4 py-3">
                <pre className="text-[13px] font-mono text-foreground bg-muted rounded-md p-3 overflow-auto max-h-48">
                  {p.config}
                </pre>
              </div>
            )}
          </div>
        ))}
        {!isLoading && pipelines.length === 0 && (
          <div className="rounded-lg border border-border bg-card px-4 py-12 text-center text-muted-foreground">
            <div className="flex flex-col items-center gap-2">
              <GitBranch size={24} className="text-muted-foreground/40" />
              <p className="text-[13px]">No pipelines yet.</p>
            </div>
          </div>
        )}
      </div>
    </PageLayout>
  )
}
