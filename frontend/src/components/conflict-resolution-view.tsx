/** Side-by-side conflict comparison for approver resolution. */

import { useState } from 'react'

interface ConflictField {
  field: string
  values: string[]
}

interface ConflictResolutionViewProps {
  conflicts: ConflictField[]
  onResolve: (resolutions: Record<string, string>) => void
  isLoading?: boolean
}

export function ConflictResolutionView({ conflicts, onResolve, isLoading }: ConflictResolutionViewProps) {
  const [resolutions, setResolutions] = useState<Record<string, string>>({})

  const allResolved = conflicts.every((c) => resolutions[c.field])

  const handleResolve = () => {
    if (allResolved) onResolve(resolutions)
  }

  return (
    <div className="space-y-4">
      <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-3">
        <p className="text-sm text-orange-800 font-medium">
          Conflicting corrections detected — select the correct value for each field.
        </p>
      </div>

      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted border-b border-border">
              <th className="text-left px-4 py-2 font-medium text-muted-foreground">Field</th>
              <th className="text-left px-4 py-2 font-medium text-muted-foreground">Reviewer Values</th>
              <th className="text-left px-4 py-2 font-medium text-muted-foreground">Resolution</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {conflicts.map((conflict) => (
              <tr key={conflict.field}>
                <td className="px-4 py-3 font-mono text-xs text-foreground">{conflict.field}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {conflict.values.map((val, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => setResolutions({ ...resolutions, [conflict.field]: val })}
                        className={`px-2 py-1 text-xs rounded border transition-colors ${
                          resolutions[conflict.field] === val
                            ? 'bg-primary/10 border-primary/30 text-primary font-medium'
                            : 'bg-card border-border text-muted-foreground hover:border-border'
                        }`}
                      >
                        {val}
                      </button>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {resolutions[conflict.field] ? (
                    <span className="text-xs font-medium text-green-700">{resolutions[conflict.field]}</span>
                  ) : (
                    <span className="text-xs text-muted-foreground/70">Select a value</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleResolve}
          disabled={!allResolved || isLoading}
          className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
        >
          {isLoading ? 'Submitting...' : 'Submit Resolution'}
        </button>
      </div>
    </div>
  )
}
