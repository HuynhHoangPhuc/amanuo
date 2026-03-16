/** Template marketplace page — browse and import curated schema templates. */

import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import { PageLayout } from '#/components/page-layout'
import { useToast } from '#/components/toast-provider'
import { TemplateCard } from '#/components/template-card'
import type { TemplateListResponse } from '#/lib/types'

export const Route = createFileRoute('/templates')({ component: TemplatesPage })

const CATEGORIES = ['all', 'invoice', 'receipt', 'identity', 'medical'] as const
type Category = (typeof CATEGORIES)[number]

function TemplatesPage() {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [category, setCategory] = useState<Category>('all')
  const [search, setSearch] = useState('')
  const [importingId, setImportingId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.templates.list(category === 'all' ? undefined : category, undefined, search || undefined),
    queryFn: () => {
      const params = new URLSearchParams()
      if (category !== 'all') params.set('category', category)
      if (search) params.set('search', search)
      params.set('limit', '50')
      return api.get<TemplateListResponse>(`/templates?${params}`)
    },
    staleTime: 30_000,
  })

  const importMutation = useMutation({
    mutationFn: (id: string) => api.post(`/templates/${id}/import`),
    onMutate: (id) => setImportingId(id),
    onSuccess: () => {
      setImportingId(null)
      qc.invalidateQueries({ queryKey: queryKeys.templates.all() })
      toast('Template imported — fields are ready to use in a new schema', 'success')
    },
    onError: (e: Error) => {
      setImportingId(null)
      toast(e.message, 'error')
    },
  })

  const templates = data?.templates ?? []

  return (
    <PageLayout title="Template Marketplace">
      {/* Category filter tabs */}
      <div className="flex items-center gap-1 mb-4 flex-wrap">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={`rounded-lg px-3 py-1.5 text-sm capitalize transition-colors ${
              category === c
                ? 'bg-blue-600 text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {c}
          </button>
        ))}

        {/* Search */}
        <div className="ml-auto flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-1.5">
          <Search size={14} className="text-gray-400" />
          <input
            className="text-sm focus:outline-none w-40 placeholder-gray-400"
            placeholder="Search templates…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-gray-100 bg-white h-36 animate-pulse" />
          ))}
        </div>
      ) : templates.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white py-16 text-center text-gray-400 text-sm">
          No templates found.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((t) => (
            <TemplateCard
              key={t.id}
              template={t}
              onImport={(id) => importMutation.mutate(id)}
              importing={importingId === t.id}
            />
          ))}
        </div>
      )}
    </PageLayout>
  )
}
