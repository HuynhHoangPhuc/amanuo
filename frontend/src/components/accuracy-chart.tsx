/** Accuracy trend line chart — lightweight SVG implementation (no charting lib). */

import type { AccuracyMetric } from '#/lib/types'

interface AccuracyChartProps {
  metrics: AccuracyMetric[]
}

export function AccuracyChart({ metrics }: AccuracyChartProps) {
  if (metrics.length === 0) {
    return <p className="text-sm text-gray-400 py-8 text-center">No accuracy data yet.</p>
  }

  // Sort chronologically and take last 30 points
  const sorted = [...metrics].sort((a, b) => a.period_end.localeCompare(b.period_end)).slice(-30)
  const width = 600
  const height = 200
  const padding = { top: 20, right: 20, bottom: 30, left: 40 }
  const chartW = width - padding.left - padding.right
  const chartH = height - padding.top - padding.bottom

  const xScale = (i: number) => padding.left + (i / Math.max(sorted.length - 1, 1)) * chartW
  const yScale = (pct: number) => padding.top + chartH - (pct / 100) * chartH

  // Build polyline points
  const points = sorted.map((m, i) => `${xScale(i)},${yScale(m.accuracy_pct)}`).join(' ')

  // Y-axis labels
  const yLabels = [0, 25, 50, 75, 100]

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full max-w-[600px]">
        {/* Grid lines */}
        {yLabels.map((pct) => (
          <g key={pct}>
            <line
              x1={padding.left} y1={yScale(pct)}
              x2={width - padding.right} y2={yScale(pct)}
              stroke="#e5e7eb" strokeWidth={1}
            />
            <text x={padding.left - 5} y={yScale(pct) + 4} textAnchor="end" className="text-[10px] fill-gray-400">
              {pct}%
            </text>
          </g>
        ))}

        {/* Line */}
        <polyline fill="none" stroke="#3b82f6" strokeWidth={2} points={points} />

        {/* Data points */}
        {sorted.map((m, i) => (
          <circle
            key={i}
            cx={xScale(i)} cy={yScale(m.accuracy_pct)}
            r={3} fill="#3b82f6"
          >
            <title>{`${m.period_end.slice(0, 10)}: ${m.accuracy_pct.toFixed(1)}%`}</title>
          </circle>
        ))}

        {/* X-axis labels (first, middle, last) */}
        {[0, Math.floor(sorted.length / 2), sorted.length - 1]
          .filter((i, idx, arr) => arr.indexOf(i) === idx && sorted[i])
          .map((i) => (
            <text key={i} x={xScale(i)} y={height - 5} textAnchor="middle" className="text-[9px] fill-gray-400">
              {sorted[i].period_end.slice(5, 10)}
            </text>
          ))}
      </svg>
    </div>
  )
}
