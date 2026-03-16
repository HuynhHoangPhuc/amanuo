/** Schema management: list, create, delete extraction schemas. */

import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { SchemaResponse, SchemaCreateRequest, SchemaField } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { TableRowSkeleton } from '#/components/loading-skeleton'
import { useToast } from '#/components/toast-provider'
import { Plus, Trash2 } from 'lucide-react'

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
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-lg rounded-xl bg-white shadow-xl p-6 space-y-4"
      >
        <h2 className="text-base font-semibold text-gray-900">New Schema</h2>
        <input
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Schema name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {fields.map((f, i) => (
            <div key={i} className="flex gap-2 items-center">
              <input
                className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Field label"
                value={f.label}
                onChange={(e) => updateField(i, { label: e.target.value })}
                required
              />
              <select
                className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none"
                value={f.type}
                onChange={(e) => updateField(i, { type: e.target.value as SchemaField['type'] })}
              >
                {FIELD_TYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
              <select
                className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none"
                value={f.occurrence}
                onChange={(e) => updateField(i, { occurrence: e.target.value as SchemaField['occurrence'] })}
              >
                {OCCURRENCES.map((o) => <option key={o}>{o}</option>)}
              </select>
              <button type="button" onClick={() => removeField(i)} className="text-red-400 hover:text-red-600">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
        <button type="button" onClick={addField} className="text-sm text-blue-600 hover:underline flex items-center gap-1">
          <Plus size={14} /> Add field
        </button>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50">
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

function SchemasPage() {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)

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
      actions={
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700"
        >
          <Plus size={14} /> New Schema
        </button>
      }
    >
      {showForm && <CreateSchemaForm onClose={() => setShowForm(false)} />}
      <div className="rounded-xl border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-xs text-gray-500">
              <th className="px-5 py-3 text-left font-medium">Name</th>
              <th className="px-5 py-3 text-left font-medium">Fields</th>
              <th className="px-5 py-3 text-left font-medium">Updated</th>
              <th className="px-5 py-3 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading && Array.from({ length: 3 }).map((_, i) => <TableRowSkeleton key={i} cols={4} />)}
            {!isLoading && schemas.map((s) => (
              <tr key={s.id} className="hover:bg-gray-50">
                <td className="px-5 py-3 font-medium text-gray-900">{s.name}</td>
                <td className="px-5 py-3 text-gray-500">{s.fields.length} fields</td>
                <td className="px-5 py-3 text-gray-500 text-xs">{new Date(s.updated_at).toLocaleString()}</td>
                <td className="px-5 py-3 text-right">
                  <button
                    onClick={() => deleteMutation.mutate(s.id)}
                    className="text-red-400 hover:text-red-600 p-1"
                    title="Delete schema"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
            {!isLoading && schemas.length === 0 && (
              <tr>
                <td colSpan={4} className="px-5 py-8 text-center text-gray-400">No schemas yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </PageLayout>
  )
}
