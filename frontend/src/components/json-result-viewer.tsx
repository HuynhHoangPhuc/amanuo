/** Collapsible JSON result viewer with confidence indicators. */

import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { ExtractionResult } from '#/lib/types'

interface JsonResultViewerProps {
  results: ExtractionResult[]
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color =
    pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 rounded-full bg-gray-200">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500">{pct}%</span>
    </div>
  )
}

export function JsonResultViewer({ results }: JsonResultViewerProps) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 border-b border-gray-100"
      >
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        Extraction Results ({results.length} fields)
      </button>

      {expanded && (
        <div className="divide-y divide-gray-100">
          {results.map((r, i) => (
            <div key={i} className="flex items-center justify-between px-4 py-2.5">
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-xs font-medium text-gray-500 w-32 shrink-0 truncate">
                  {r.label}
                </span>
                <span className="text-sm text-gray-900 truncate">
                  {r.value === null || r.value === undefined
                    ? <span className="text-gray-400 italic">null</span>
                    : String(r.value)}
                </span>
              </div>
              <ConfidenceBar value={r.confidence} />
            </div>
          ))}
        </div>
      )}

      <div className="px-4 py-2 bg-gray-50 border-t border-gray-100">
        <details>
          <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-700">
            Raw JSON
          </summary>
          <pre className="mt-2 text-xs text-gray-700 overflow-auto max-h-64 bg-gray-100 rounded p-2">
            {JSON.stringify(results, null, 2)}
          </pre>
        </details>
      </div>
    </div>
  )
}
