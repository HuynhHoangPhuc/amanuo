/** Editable list of AI-suggested schema fields with confidence badges. */

import { Trash2, Plus } from 'lucide-react'
import type { SuggestedField } from '#/lib/types'

const FIELD_TYPES = ['text', 'number', 'date', 'boolean'] as const
const OCCURRENCES = ['required once', 'optional once', 'optional multiple'] as const

function confidenceColor(score: number): string {
  if (score >= 0.8) return 'bg-green-500/15 text-green-700'
  if (score >= 0.5) return 'bg-yellow-500/15 text-yellow-700'
  return 'bg-red-500/15 text-red-600'
}

interface SuggestedFieldsEditorProps {
  fields: SuggestedField[]
  onChange: (fields: SuggestedField[]) => void
}

export function SuggestedFieldsEditor({ fields, onChange }: SuggestedFieldsEditorProps) {
  const update = (i: number, patch: Partial<SuggestedField>) =>
    onChange(fields.map((f, idx) => (idx === i ? { ...f, ...patch } : f)))

  const remove = (i: number) => onChange(fields.filter((_, idx) => idx !== i))

  const addEmpty = () =>
    onChange([...fields, { label: '', type: 'text', occurrence: 'optional once', confidence: 1 }])

  return (
    <div className="space-y-2">
      {fields.map((f, i) => (
        <div key={i} className="flex gap-2 items-center">
          <input
            className="flex-1 min-w-0 rounded-md border border-border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="field_label"
            value={f.label}
            onChange={(e) => update(i, { label: e.target.value })}
          />
          <select
            className="rounded-md border border-border px-2 py-1.5 text-sm focus:outline-none"
            value={f.type}
            onChange={(e) => update(i, { type: e.target.value as SuggestedField['type'] })}
          >
            {FIELD_TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>
          <select
            className="rounded-md border border-border px-2 py-1.5 text-sm focus:outline-none"
            value={f.occurrence}
            onChange={(e) => update(i, { occurrence: e.target.value })}
          >
            {OCCURRENCES.map((o) => <option key={o}>{o}</option>)}
          </select>
          <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${confidenceColor(f.confidence)}`}>
            {Math.round(f.confidence * 100)}%
          </span>
          <button
            type="button"
            onClick={() => remove(i)}
            className="shrink-0 text-red-400 hover:text-red-600"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={addEmpty}
        className="text-sm text-primary hover:underline flex items-center gap-1 mt-1"
      >
        <Plus size={14} /> Add field
      </button>
    </div>
  )
}
