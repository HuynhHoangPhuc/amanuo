/** Settings page: API key management (create, list, revoke). */

import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, setApiKey, clearApiKey, hasApiKey } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { ApiKeyResponse, ApiKeyCreateResponse } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { TableRowSkeleton } from '#/components/loading-skeleton'
import { useToast } from '#/components/toast-provider'
import { Plus, Trash2, Copy, Eye, EyeOff, Key } from 'lucide-react'

export const Route = createFileRoute('/settings')({ component: SettingsPage })

function ActiveKeyBanner() {
  const [visible, setVisible] = useState(false)
  const { toast } = useToast()
  const key = localStorage.getItem('amanuo_api_key') ?? ''

  if (!hasApiKey()) return null

  const masked = visible ? key : `${key.slice(0, 8)}${'•'.repeat(24)}`

  const copy = () => {
    navigator.clipboard.writeText(key)
    toast('API key copied', 'success')
  }

  return (
    <div className="rounded-xl border border-primary/20 bg-primary/10 p-4 flex items-center gap-3 mb-4">
      <Key size={16} className="text-primary shrink-0" />
      <span className="text-sm text-primary font-mono flex-1 truncate">{masked}</span>
      <button onClick={() => setVisible(!visible)} className="text-primary/70 hover:text-primary">
        {visible ? <EyeOff size={14} /> : <Eye size={14} />}
      </button>
      <button onClick={copy} className="text-primary/70 hover:text-primary">
        <Copy size={14} />
      </button>
      <button
        onClick={() => { clearApiKey(); window.location.reload() }}
        className="text-xs text-red-500 hover:text-red-700 border border-red-500/20 rounded px-2 py-0.5"
      >
        Clear
      </button>
    </div>
  )
}

function NewKeyResult({ apiKey, onDismiss }: { apiKey: string; onDismiss: () => void }) {
  const { toast } = useToast()
  const copy = () => { navigator.clipboard.writeText(apiKey); toast('Copied!', 'success') }
  return (
    <div className="rounded-xl border border-green-500/20 bg-green-500/10 p-4 space-y-2 mb-4">
      <p className="text-sm font-medium text-green-700 dark:text-green-400">API key created — copy it now, it won't be shown again.</p>
      <div className="flex items-center gap-2">
        <code className="flex-1 text-xs bg-card border border-green-500/20 rounded px-3 py-2 font-mono break-all">
          {apiKey}
        </code>
        <button onClick={copy} className="p-2 text-green-600 hover:text-green-700 dark:text-green-400">
          <Copy size={14} />
        </button>
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => { setApiKey(apiKey); toast('Active key updated', 'success'); onDismiss() }}
          className="text-xs rounded-lg bg-green-600 text-white px-3 py-1.5 hover:bg-green-700"
        >
          Use this key
        </button>
        <button onClick={onDismiss} className="text-xs text-muted-foreground hover:text-foreground">
          Dismiss
        </button>
      </div>
    </div>
  )
}

function SettingsPage() {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [keyName, setKeyName] = useState('')
  const [newKey, setNewKey] = useState<string | null>(null)

  const { data: apiKeys = [], isLoading } = useQuery({
    queryKey: queryKeys.apiKeys.list(),
    queryFn: () => api.get<ApiKeyResponse[]>('/api-keys'),
  })

  const createMutation = useMutation({
    mutationFn: (name: string) =>
      api.post<ApiKeyCreateResponse>('/api-keys', { name }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: queryKeys.apiKeys.list() })
      setNewKey(data.key)
      setKeyName('')
    },
    onError: (e: Error) => toast(e.message, 'error'),
  })

  const revokeMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api-keys/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.apiKeys.list() })
      toast('API key revoked', 'success')
    },
    onError: (e: Error) => toast(e.message, 'error'),
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    if (keyName.trim()) createMutation.mutate(keyName.trim())
  }

  return (
    <PageLayout title="Settings">
      <div className="max-w-2xl space-y-6">
        <ActiveKeyBanner />

        {newKey && (
          <NewKeyResult apiKey={newKey} onDismiss={() => setNewKey(null)} />
        )}

        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Create API Key</h2>
          <form onSubmit={handleCreate} className="flex gap-2">
            <input
              className="flex-1 rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Key name (e.g. production)"
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
              required
            />
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              <Plus size={14} />
              {createMutation.isPending ? 'Creating…' : 'Create'}
            </button>
          </form>
        </div>

        <div className="rounded-xl border border-border bg-card">
          <div className="px-5 py-4 border-b border-border/50">
            <h2 className="text-sm font-semibold text-foreground">API Keys</h2>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/50 text-xs text-muted-foreground">
                <th className="px-5 py-2 text-left font-medium">Name</th>
                <th className="px-5 py-2 text-left font-medium">Prefix</th>
                <th className="px-5 py-2 text-left font-medium">Last Used</th>
                <th className="px-5 py-2 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {isLoading && Array.from({ length: 2 }).map((_, i) => (
                <TableRowSkeleton key={i} cols={4} />
              ))}
              {!isLoading && apiKeys.map((k) => (
                <tr key={k.id} className={`hover:bg-muted ${!k.active ? 'opacity-50' : ''}`}>
                  <td className="px-5 py-2.5 font-medium text-foreground">{k.name}</td>
                  <td className="px-5 py-2.5 font-mono text-xs text-muted-foreground">{k.key_prefix}…</td>
                  <td className="px-5 py-2.5 text-xs text-muted-foreground">
                    {k.last_used_at ? new Date(k.last_used_at).toLocaleString() : 'Never'}
                  </td>
                  <td className="px-5 py-2.5 text-right">
                    <button
                      onClick={() => revokeMutation.mutate(k.id)}
                      disabled={!k.active}
                      className="text-red-400 hover:text-red-600 p-1 disabled:opacity-30"
                      title="Revoke key"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
              {!isLoading && apiKeys.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-5 py-8 text-center text-muted-foreground/70">
                    No API keys yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </PageLayout>
  )
}
