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
import { Plus, Trash2 } from 'lucide-react'

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
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-2xl rounded-xl bg-white shadow-xl p-6 space-y-4"
      >
        <h2 className="text-base font-semibold text-gray-900">New Pipeline</h2>
        <input
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Pipeline name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Config (YAML)
          </label>
          <textarea
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
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
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {mutation.isPending ? 'Creating…' : 'Create'}
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
      actions={
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700"
        >
          <Plus size={14} /> New Pipeline
        </button>
      }
    >
      {showForm && <CreatePipelineForm onClose={() => setShowForm(false)} />}
      <div className="space-y-3">
        {isLoading &&
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-gray-200 bg-white p-4">
              <TableRowSkeleton cols={1} />
            </div>
          ))}
        {!isLoading && pipelines.map((p) => (
          <div key={p.id} className="rounded-xl border border-gray-200 bg-white">
            <div
              className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-gray-50"
              onClick={() => setExpanded(expanded === p.id ? null : p.id)}
            >
              <div>
                <p className="font-medium text-gray-900 text-sm">{p.name}</p>
                {p.description && (
                  <p className="text-xs text-gray-500 mt-0.5">{p.description}</p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-400">
                  {new Date(p.updated_at).toLocaleDateString()}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(p.id) }}
                  className="text-red-400 hover:text-red-600 p-1"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
            {expanded === p.id && (
              <div className="border-t border-gray-100 px-5 py-3">
                <pre className="text-xs font-mono text-gray-700 bg-gray-50 rounded-lg p-3 overflow-auto max-h-48">
                  {p.config}
                </pre>
              </div>
            )}
          </div>
        ))}
        {!isLoading && pipelines.length === 0 && (
          <div className="rounded-xl border border-gray-200 bg-white px-5 py-10 text-center text-gray-400 text-sm">
            No pipelines yet.
          </div>
        )}
      </div>
    </PageLayout>
  )
}
