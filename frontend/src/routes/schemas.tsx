/** Schema management: list, create, delete extraction schemas. */

import { useState } from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { SchemaResponse, SchemaCreateRequest, SchemaField } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { TableRowSkeleton } from '#/components/loading-skeleton'
import { useToast } from '#/components/toast-provider'
import { SchemaSuggestForm } from '#/components/schema-suggest-form'
import { Plus, Trash2, Sparkles, LayoutGrid, FileText } from 'lucide-react'

export const Route = createFileRoute('/schemas')({ component: SchemasPage })

const FIELD_TYPES = ['text', 'number', 'date', 'boolean'] as const
const OCCURRENCES = ['required once', 'optional once', 'optional multiple'] as const

function CreateSchemaForm({ onClose }: { onClose: () => void }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [fields, setFields] = useState<SchemaField[]>([
    { label: '', type: 'text', occurrence: 'required once' },
  ])

  const mutation = useMutation({
    mutationFn: (req: SchemaCreateRequest) => api.post<SchemaResponse>('/schemas', req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.schemas.list() })
      toast('Schema created', 'success')
      onClose()
    },
    onError: (e: Error) => toast(e.message, 'error'),
  })

  const addField = () =>
    setFields((f) => [...f, { label: '', type: 'text', occurrence: 'required once' }])

  const removeField = (i: number) =>
    setFields((f) => f.filter((_, idx) => idx !== i))

  const updateField = (i: number, patch: Partial<SchemaField>) =>
    setFields((f) => f.map((field, idx) => (idx === i ? { ...field, ...patch } : field)))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate({ name, fields })
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-lg rounded-lg border border-border bg-card shadow-lg p-6 space-y-4"
      >
        <h2 className="text-base font-semibold text-foreground">New Schema</h2>
        <input
          className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="Schema name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {fields.map((f, i) => (
            <div key={i} className="flex gap-2 items-center">
              <input
                className="flex-1 rounded-md border border-input bg-transparent px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Field label"
                value={f.label}
                onChange={(e) => updateField(i, { label: e.target.value })}
                required
              />
              <select
                className="rounded-md border border-input bg-transparent px-2 py-1.5 text-sm focus:outline-none cursor-pointer"
                value={f.type}
                onChange={(e) => updateField(i, { type: e.target.value as SchemaField['type'] })}
              >
                {FIELD_TYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
              <select
                className="rounded-md border border-input bg-transparent px-2 py-1.5 text-sm focus:outline-none cursor-pointer"
                value={f.occurrence}
                onChange={(e) => updateField(i, { occurrence: e.target.value as SchemaField['occurrence'] })}
              >
                {OCCURRENCES.map((o) => <option key={o}>{o}</option>)}
              </select>
              <button type="button" onClick={() => removeField(i)} className="text-red-400 hover:text-red-600 p-1 cursor-pointer transition-colors">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
        <button type="button" onClick={addField} className="text-sm text-primary hover:underline flex items-center gap-1 cursor-pointer">
          <Plus size={14} /> Add field
        </button>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-md border border-border hover:bg-accent cursor-pointer transition-colors">
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

function SchemasPage() {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [showSuggest, setShowSuggest] = useState(false)

  const { data: schemas = [], isLoading } = useQuery({
    queryKey: queryKeys.schemas.list(),
    queryFn: () => api.get<SchemaResponse[]>('/schemas'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/schemas/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.schemas.list() })
      toast('Schema deleted', 'success')
    },
    onError: (e: Error) => toast(e.message, 'error'),
  })

  return (
    <PageLayout
      title="Schemas"
      description="Define extraction field templates"
      actions={
        <div className="flex items-center gap-2">
          <Link
            to="/templates"
            className="flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-[13px] font-medium text-foreground hover:bg-accent no-underline cursor-pointer transition-colors"
          >
            <LayoutGrid size={14} /> Templates
          </Link>
          <button
            onClick={() => setShowSuggest(true)}
            className="flex items-center gap-1.5 rounded-md border border-primary/20 bg-primary/10 px-3 py-1.5 text-[13px] font-medium text-primary hover:bg-primary/15 cursor-pointer transition-colors"
          >
            <Sparkles size={14} /> Auto-Suggest
          </button>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-[13px] font-medium text-primary-foreground hover:bg-primary/90 cursor-pointer transition-colors"
          >
            <Plus size={14} /> New Schema
          </button>
        </div>
      }
    >
      {showForm && <CreateSchemaForm onClose={() => setShowForm(false)} />}
      {showSuggest && <SchemaSuggestForm onClose={() => setShowSuggest(false)} />}
      <div className="rounded-lg border border-border bg-card">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-border">
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Name</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Fields</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Updated</th>
                <th className="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && Array.from({ length: 3 }).map((_, i) => <TableRowSkeleton key={i} cols={4} />)}
              {!isLoading && schemas.map((s) => (
                <tr key={s.id} className="border-b border-border/50 hover:bg-accent/50 transition-colors">
                  <td className="px-4 py-2.5 font-medium text-foreground">{s.name}</td>
                  <td className="px-4 py-2.5 text-muted-foreground tabular-nums">{s.fields.length} fields</td>
                  <td className="px-4 py-2.5 text-muted-foreground text-[12px] tabular-nums">{new Date(s.updated_at).toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      onClick={() => deleteMutation.mutate(s.id)}
                      className="text-red-400 hover:text-red-600 p-1 cursor-pointer transition-colors"
                      title="Delete schema"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
              {!isLoading && schemas.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-12 text-center text-muted-foreground">
                    <div className="flex flex-col items-center gap-2">
                      <FileText size={24} className="text-muted-foreground/40" />
                      <p className="text-[13px]">No schemas yet. Create one to start extracting.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </PageLayout>
  )
}
