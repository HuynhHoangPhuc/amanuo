/** TanStack Query key factories for cache invalidation. */

export const queryKeys = {
  jobs: {
    all: () => ['jobs'] as const,
    list: (status?: string) => ['jobs', 'list', status] as const,
    detail: (id: string) => ['jobs', 'detail', id] as const,
  },
  schemas: {
    all: () => ['schemas'] as const,
    list: () => ['schemas', 'list'] as const,
    detail: (id: string) => ['schemas', 'detail', id] as const,
    versions: (id: string) => ['schemas', id, 'versions'] as const,
  },
  pipelines: {
    all: () => ['pipelines'] as const,
    list: () => ['pipelines', 'list'] as const,
    detail: (id: string) => ['pipelines', 'detail', id] as const,
  },
  batches: {
    all: () => ['batches'] as const,
    list: () => ['batches', 'list'] as const,
    detail: (id: string) => ['batches', 'detail', id] as const,
  },
  webhooks: {
    all: () => ['webhooks'] as const,
    list: () => ['webhooks', 'list'] as const,
    deliveries: (id: string) => ['webhooks', id, 'deliveries'] as const,
  },
  apiKeys: {
    all: () => ['api-keys'] as const,
    list: () => ['api-keys', 'list'] as const,
  },
  templates: {
    all: () => ['templates'] as const,
    list: (category?: string, lang?: string, search?: string) =>
      ['templates', 'list', category, lang, search] as const,
    detail: (id: string) => ['templates', 'detail', id] as const,
  },
}
