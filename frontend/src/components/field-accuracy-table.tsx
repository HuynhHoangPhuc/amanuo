/** Per-field accuracy breakdown table with color-coded rows. */

import type { FieldAccuracyDetail } from '#/lib/types'

interface FieldAccuracyTableProps {
  fieldAccuracy: Record<string, FieldAccuracyDetail>
}

function accuracyColor(pct: number): string {
  if (pct >= 95) return 'bg-green-50 text-green-700'
  if (pct >= 80) return 'bg-yellow-50 text-yellow-700'
  return 'bg-red-50 text-red-700'
}

export function FieldAccuracyTable({ fieldAccuracy }: FieldAccuracyTableProps) {
  const entries = Object.entries(fieldAccuracy).sort(
    ([, a], [, b]) => a.accuracy_pct - b.accuracy_pct,
  )

  if (entries.length === 0) {
    return <p className="text-sm text-gray-400 py-4 text-center">No field-level data yet.</p>
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Field</th>
            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Accuracy</th>
            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Correct</th>
            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {entries.map(([field, stats]) => (
            <tr key={field} className="hover:bg-gray-50">
              <td className="px-4 py-2 font-medium text-gray-700">{field}</td>
              <td className="px-4 py-2 text-right">
                <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${accuracyColor(stats.accuracy_pct)}`}>
                  {stats.accuracy_pct.toFixed(1)}%
                </span>
              </td>
              <td className="px-4 py-2 text-right text-gray-600">{stats.correct}</td>
              <td className="px-4 py-2 text-right text-gray-600">{stats.total}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
