/** Horizontal step indicator showing approval round progress. */

import type { ReviewStatusResponse } from '#/lib/types'

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-muted text-muted-foreground',
  in_progress: 'bg-primary text-primary-foreground',
  completed: 'bg-green-500/100 text-white',
  escalated: 'bg-orange-500/100 text-white',
}

interface ApprovalProgressProps {
  status: ReviewStatusResponse
}

export function ApprovalProgress({ status }: ApprovalProgressProps) {
  const totalSteps = status.total_rounds ?? status.current_round
  const steps = Array.from({ length: totalSteps }, (_, i) => i + 1)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="font-medium">{status.policy_name}</span>
        <span className="capitalize">{status.policy_type}</span>
      </div>

      {status.policy_type === 'chain' ? (
        <div className="flex items-center gap-1">
          {steps.map((step) => {
            const isCurrent = step === status.current_round
            const isComplete = step < status.current_round
            const color = isComplete
              ? 'bg-green-500/100 text-white'
              : isCurrent
                ? STATUS_COLORS[status.round_status] ?? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground'
            return (
              <div key={step} className="flex items-center gap-1">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium ${color}`}>
                  {step}
                </div>
                {step < totalSteps && (
                  <div className={`w-6 h-0.5 ${isComplete ? 'bg-green-500/100' : 'bg-muted'}`} />
                )}
              </div>
            )
          })}
        </div>
      ) : (
        /* Quorum: show M/N progress bar */
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Approvals</span>
            <span>
              {status.assignments.filter((a) => a.status === 'approved' || a.status === 'corrected').length}
              {' / '}
              {status.assignments.length}
            </span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary/100 rounded-full transition-all"
              style={{
                width: `${(status.assignments.filter((a) => a.status === 'approved' || a.status === 'corrected').length / Math.max(status.assignments.length, 1)) * 100}%`,
              }}
            />
          </div>
        </div>
      )}

      {status.deadline_at && (
        <p className="text-xs text-muted-foreground/70">
          Deadline: {new Date(status.deadline_at).toLocaleString()}
        </p>
      )}

      {status.round_status === 'escalated' && (
        <p className="text-xs text-orange-600 font-medium">Escalated — awaiting approver resolution</p>
      )}
    </div>
  )
}
