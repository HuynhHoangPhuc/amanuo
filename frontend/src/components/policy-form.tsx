/** Create/edit approval policy form with chain/quorum config. */

import { useState } from 'react'
import type { PolicyType } from '#/lib/types'

interface PolicyFormProps {
  onSubmit: (data: PolicyFormData) => void
  onCancel: () => void
  isLoading?: boolean
}

export interface PolicyFormData {
  name: string
  policy_type: PolicyType
  config: Record<string, unknown>
  deadline_hours: number | null
}

export function PolicyForm({ onSubmit, onCancel, isLoading }: PolicyFormProps) {
  const [name, setName] = useState('')
  const [policyType, setPolicyType] = useState<PolicyType>('chain')
  const [deadlineHours, setDeadlineHours] = useState('')

  // Chain config
  const [steps, setSteps] = useState([{ role: 'reviewer', label: 'Review' }])

  // Quorum config
  const [required, setRequired] = useState(2)
  const [poolSize, setPoolSize] = useState(3)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const config =
      policyType === 'chain'
        ? { steps }
        : { required, pool_size: poolSize, pool_role: 'reviewer', escalation_role: 'approver' }

    onSubmit({
      name,
      policy_type: policyType,
      config,
      deadline_hours: deadlineHours ? parseInt(deadlineHours) : null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-foreground mb-1">Policy Name</label>
        <input
          type="text" value={name} onChange={(e) => setName(e.target.value)}
          required className="w-full rounded-md border border-border px-3 py-2 text-sm focus:ring-2 focus:ring-ring focus:border-ring"
          placeholder="e.g. Legal Review Chain"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-foreground mb-1">Type</label>
        <select
          value={policyType} onChange={(e) => setPolicyType(e.target.value as PolicyType)}
          className="w-full rounded-md border border-border px-3 py-2 text-sm"
        >
          <option value="chain">Chain (sequential)</option>
          <option value="quorum">Quorum (M-of-N voting)</option>
        </select>
      </div>

      {policyType === 'chain' ? (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-foreground">Steps</label>
          {steps.map((step, i) => (
            <div key={i} className="flex gap-2 items-center">
              <span className="text-xs text-muted-foreground/70 w-4">{i + 1}.</span>
              <select
                value={step.role}
                onChange={(e) => {
                  const next = [...steps]
                  next[i] = { ...step, role: e.target.value }
                  setSteps(next)
                }}
                className="flex-1 rounded-md border border-border px-2 py-1.5 text-sm"
              >
                <option value="reviewer">Reviewer</option>
                <option value="approver">Approver</option>
              </select>
              <input
                value={step.label} placeholder="Label"
                onChange={(e) => {
                  const next = [...steps]
                  next[i] = { ...step, label: e.target.value }
                  setSteps(next)
                }}
                className="flex-1 rounded-md border border-border px-2 py-1.5 text-sm"
              />
              {steps.length > 1 && (
                <button type="button" onClick={() => setSteps(steps.filter((_, j) => j !== i))}
                  className="text-red-500 text-xs hover:text-red-700">Remove</button>
              )}
            </div>
          ))}
          <button type="button"
            onClick={() => setSteps([...steps, { role: 'reviewer', label: '' }])}
            className="text-sm text-primary hover:text-primary"
          >+ Add step</button>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Required approvals</label>
            <input type="number" min={1} value={required}
              onChange={(e) => setRequired(parseInt(e.target.value) || 1)}
              className="w-full rounded-md border border-border px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Pool size</label>
            <input type="number" min={1} value={poolSize}
              onChange={(e) => setPoolSize(parseInt(e.target.value) || 1)}
              className="w-full rounded-md border border-border px-3 py-2 text-sm" />
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-foreground mb-1">Deadline (hours, optional)</label>
        <input type="number" min={1} value={deadlineHours}
          onChange={(e) => setDeadlineHours(e.target.value)}
          className="w-full rounded-md border border-border px-3 py-2 text-sm"
          placeholder="e.g. 48" />
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <button type="button" onClick={onCancel}
          className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground">Cancel</button>
        <button type="submit" disabled={isLoading || !name}
          className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50">
          {isLoading ? 'Creating...' : 'Create Policy'}
        </button>
      </div>
    </form>
  )
}
