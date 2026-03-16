/** Webhook subscription management and delivery log. */

import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { WebhookSubscription, WebhookDelivery, WebhookEvent } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { StatusBadge } from '#/components/status-badge'
import { TableRowSkeleton } from '#/components/loading-skeleton'
import { useToast } from '#/components/toast-provider'
import { Plus, Trash2, Send, ChevronDown, ChevronRight } from 'lucide-react'

export const Route = createFileRoute('/webhooks')({ component: WebhooksPage })

const ALL_EVENTS: WebhookEvent[] = [
  'job.completed', 'job.failed', 'batch.completed', 'batch.failed',
]

function CreateWebhookForm({ onClose }: { onClose: () => void }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [url, setUrl] = useState('')
  const [events, setEvents] = useState<WebhookEvent[]>(['job.completed'])

  const mutation = useMutation({
    mutationFn: (body: { url: string; events: WebhookEvent[] }) =>
      api.post<WebhookSubscription>('/webhooks', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.webhooks.list() })
      toast('Webhook created', 'success')
      onClose()
    },
    onError: (e: Error) => toast(e.message, 'error'),
  })

  const toggleEvent = (ev: WebhookEvent) =>
    setEvents((prev) =>
      prev.includes(ev) ? prev.filter((e) => e !== ev) : [...prev, ev],
    )

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30">
      <form
        onSubmit={(e) => { e.preventDefault(); mutation.mutate({ url, events }) }}
        className="w-full max-w-md rounded-xl bg-white shadow-xl p-6 space-y-4"
      >
        <h2 className="text-base font-semibold text-gray-900">New Webhook</h2>
        <input
          type="url"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="https://your-server.com/webhook"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
        />
        <div>
          <p className="text-xs font-medium text-gray-600 mb-2">Events</p>
          <div className="space-y-1.5">
            {ALL_EVENTS.map((ev) => (
              <label key={ev} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={events.includes(ev)}
                  onChange={() => toggleEvent(ev)}
                  className="rounded"
                />
                <span className="text-sm text-gray-700 font-mono">{ev}</span>
              </label>
            ))}
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50">
            Cancel
          </button>
          <button
            type="submit"
            disabled={mutation.isPending || events.length === 0}
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {mutation.isPending ? 'Creating…' : 'Create'}
          </button>
        </div>
      </form>
    </div>
  )
}

function DeliveryLog({ webhookId }: { webhookId: string }) {
  const { data: deliveries = [], isLoading } = useQuery({
    queryKey: queryKeys.webhooks.deliveries(webhookId),
    queryFn: () => api.get<WebhookDelivery[]>(`/webhooks/${webhookId}/deliveries`),
  })

  return (
    <div className="px-5 pb-3">
      <p className="text-xs font-medium text-gray-500 mb-2">Recent Deliveries</p>
      {isLoading && <TableRowSkeleton cols={3} />}
      {!isLoading && deliveries.length === 0 && (
        <p className="text-xs text-gray-400">No deliveries yet.</p>
      )}
      {!isLoading && deliveries.slice(0, 5).map((d) => (
        <div key={d.id} className="flex items-center gap-3 py-1 text-xs">
          <StatusBadge status={d.status} />
          <span className="font-mono text-gray-600">{d.event}</span>
          {d.response_status && (
            <span className="text-gray-400">HTTP {d.response_status}</span>
          )}
          <span className="text-gray-400 ml-auto">{new Date(d.created_at).toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}

function WebhookRow({ webhook }: { webhook: WebhookSubscription }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [expanded, setExpanded] = useState(false)

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/webhooks/${webhook.id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.webhooks.list() })
      toast('Webhook deleted', 'success')
    },
    onError: (e: Error) => toast(e.message, 'error'),
  })

  const testMutation = useMutation({
    mutationFn: () => api.post(`/webhooks/${webhook.id}/test`),
    onSuccess: () => toast('Test event sent', 'success'),
    onError: (e: Error) => toast(e.message, 'error'),
  })

  return (
    <div className="border-b border-gray-50 last:border-0">
      <div
        className="flex items-center gap-4 px-5 py-3 hover:bg-gray-50 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{webhook.url}</p>
          <p className="text-xs text-gray-500 mt-0.5">{webhook.events.join(', ')}</p>
        </div>
        <StatusBadge status={webhook.active ? 'active' : 'inactive'} />
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => { e.stopPropagation(); testMutation.mutate() }}
            className="p-1.5 text-gray-400 hover:text-blue-600 rounded"
            title="Send test event"
          >
            <Send size={13} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); deleteMutation.mutate() }}
            className="p-1.5 text-gray-400 hover:text-red-600 rounded"
            title="Delete webhook"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>
      {expanded && <DeliveryLog webhookId={webhook.id} />}
    </div>
  )
}

function WebhooksPage() {
  const [showForm, setShowForm] = useState(false)

  const { data: webhooks = [], isLoading } = useQuery({
    queryKey: queryKeys.webhooks.list(),
    queryFn: () => api.get<WebhookSubscription[]>('/webhooks'),
  })

  return (
    <PageLayout
      title="Webhooks"
      actions={
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700"
        >
          <Plus size={14} /> New Webhook
        </button>
      }
    >
      {showForm && <CreateWebhookForm onClose={() => setShowForm(false)} />}
      <div className="rounded-xl border border-gray-200 bg-white">
        {isLoading && Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="px-5 py-3 border-b border-gray-50">
            <TableRowSkeleton cols={3} />
          </div>
        ))}
        {!isLoading && webhooks.map((w) => <WebhookRow key={w.id} webhook={w} />)}
        {!isLoading && webhooks.length === 0 && (
          <div className="px-5 py-10 text-center text-gray-400 text-sm">
            No webhooks configured.
          </div>
        )}
      </div>
    </PageLayout>
  )
}
