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
    pct >= 80 ? 'bg-green-500/100' : pct >= 50 ? 'bg-yellow-500/100' : 'bg-red-500/100'
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 rounded-full bg-muted">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground">{pct}%</span>
    </div>
  )
}

export function JsonResultViewer({ results }: JsonResultViewerProps) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-4 py-3 text-sm font-medium text-foreground hover:bg-muted border-b border-border/50"
      >
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        Extraction Results ({results.length} fields)
      </button>

      {expanded && (
        <div className="divide-y divide-border">
          {results.map((r, i) => (
            <div key={i} className="flex items-center justify-between px-4 py-2.5">
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-xs font-medium text-muted-foreground w-32 shrink-0 truncate">
                  {r.label}
                </span>
                <span className="text-sm text-foreground truncate">
                  {r.value === null || r.value === undefined
                    ? <span className="text-muted-foreground/70 italic">null</span>
                    : String(r.value)}
                </span>
              </div>
              <ConfidenceBar value={r.confidence} />
            </div>
          ))}
        </div>
      )}

      <div className="px-4 py-2 bg-muted border-t border-border/50">
        <details>
          <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
            Raw JSON
          </summary>
          <pre className="mt-2 text-xs text-foreground overflow-auto max-h-64 bg-muted rounded p-2">
            {JSON.stringify(results, null, 2)}
          </pre>
        </details>
      </div>
    </div>
  )
}
