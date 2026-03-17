/** Per-field accuracy breakdown table with color-coded rows. */

import type { FieldAccuracyDetail } from '#/lib/types'

interface FieldAccuracyTableProps {
  fieldAccuracy: Record<string, FieldAccuracyDetail>
}

function accuracyColor(pct: number): string {
  if (pct >= 95) return 'bg-green-500/10 text-green-700'
  if (pct >= 80) return 'bg-yellow-500/10 text-yellow-700'
  return 'bg-red-500/10 text-red-700'
}

export function FieldAccuracyTable({ fieldAccuracy }: FieldAccuracyTableProps) {
  const entries = Object.entries(fieldAccuracy).sort(
    ([, a], [, b]) => a.accuracy_pct - b.accuracy_pct,
  )

  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground/70 py-4 text-center">No field-level data yet.</p>
  }

  return (
    <div className="rounded-md border border-border bg-card overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted">
            <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Field</th>
            <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">Accuracy</th>
            <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">Correct</th>
            <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {entries.map(([field, stats]) => (
            <tr key={field} className="hover:bg-muted">
              <td className="px-4 py-2 font-medium text-foreground">{field}</td>
              <td className="px-4 py-2 text-right">
                <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${accuracyColor(stats.accuracy_pct)}`}>
                  {stats.accuracy_pct.toFixed(1)}%
                </span>
              </td>
              <td className="px-4 py-2 text-right text-muted-foreground">{stats.correct}</td>
              <td className="px-4 py-2 text-right text-muted-foreground">{stats.total}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
