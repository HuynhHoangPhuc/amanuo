/** Review action toolbar — approve, submit corrections, skip. */

import { Check, Edit3, SkipForward, Loader2 } from 'lucide-react'

interface ReviewToolbarProps {
  onApprove: () => void
  onCorrect: () => void
  onSkip?: () => void
  hasChanges: boolean
  isSubmitting: boolean
}

export function ReviewToolbar({
  onApprove,
  onCorrect,
  onSkip,
  hasChanges,
  isSubmitting,
}: ReviewToolbarProps) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-muted border-t border-border rounded-b-xl">
      <button
        onClick={onApprove}
        disabled={isSubmitting}
        className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        title="Approve (Enter)"
      >
        {isSubmitting ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
        Approve
      </button>

      {hasChanges && (
        <button
          onClick={onCorrect}
          disabled={isSubmitting}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          title="Submit Corrections (Ctrl+Enter)"
        >
          {isSubmitting ? <Loader2 size={16} className="animate-spin" /> : <Edit3 size={16} />}
          Submit Corrections
        </button>
      )}

      {onSkip && (
        <button
          onClick={onSkip}
          disabled={isSubmitting}
          className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted disabled:opacity-50"
        >
          <SkipForward size={16} />
          Skip
        </button>
      )}

      <div className="ml-auto text-xs text-muted-foreground/70">
        Enter = Approve | Ctrl+Enter = Submit | Tab = Next field
      </div>
    </div>
  )
}
