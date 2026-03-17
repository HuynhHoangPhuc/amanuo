/** Inline editable field for extraction results with confidence indicator. */

import type { ExtractionResult } from '#/lib/types'

interface FieldEditorProps {
  fields: ExtractionResult[]
  onChange: (updated: ExtractionResult[]) => void
  modifiedFields?: Set<string>
}

const CONFIDENCE_LOW = 0.85

export function FieldEditor({ fields, onChange, modifiedFields }: FieldEditorProps) {
  const handleChange = (index: number, value: string) => {
    const updated = fields.map((f, i) =>
      i === index ? { ...f, value: value } : f,
    )
    onChange(updated)
  }

  return (
    <div className="space-y-3">
      {fields.map((field, index) => {
        const isLowConfidence = field.confidence < CONFIDENCE_LOW
        const isModified = modifiedFields?.has(field.label)

        return (
          <div key={field.label} className="group">
            <div className="flex items-center gap-2 mb-1">
              <label className="text-sm font-medium text-foreground">{field.label}</label>
              <span
                className={`text-xs px-1.5 py-0.5 rounded ${
                  isLowConfidence
                    ? 'bg-yellow-500/15 text-yellow-700'
                    : 'bg-green-500/10 text-green-600'
                }`}
              >
                {Math.round(field.confidence * 100)}%
              </span>
              {isModified && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                  modified
                </span>
              )}
            </div>
            <input
              type="text"
              value={String(field.value ?? '')}
              onChange={(e) => handleChange(index, e.target.value)}
              className={`w-full rounded-lg border px-3 py-2 text-sm ${
                isLowConfidence
                  ? 'border-yellow-300 bg-yellow-500/10 focus:ring-yellow-400'
                  : 'border-border bg-card focus:ring-ring'
              } focus:outline-none focus:ring-2`}
            />
          </div>
        )
      })}
    </div>
  )
}
