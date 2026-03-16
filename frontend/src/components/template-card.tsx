/** Template marketplace card — displays a single schema template with import action. */

import type { SchemaTemplate } from '#/lib/types'

interface TemplateCardProps {
  template: SchemaTemplate
  onImport: (id: string) => void
  importing: boolean
}

const CATEGORY_COLORS: Record<string, string> = {
  invoice: 'bg-blue-50 text-blue-700',
  receipt: 'bg-green-50 text-green-700',
  identity: 'bg-purple-50 text-purple-700',
  medical: 'bg-red-50 text-red-700',
  other: 'bg-gray-50 text-gray-700',
}

export function TemplateCard({ template, onImport, importing }: TemplateCardProps) {
  const categoryColor = CATEGORY_COLORS[template.category] ?? CATEGORY_COLORS.other

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 flex flex-col gap-3 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 leading-tight">{template.name}</h3>
          {template.description && (
            <p className="mt-1 text-xs text-gray-500 line-clamp-2">{template.description}</p>
          )}
        </div>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${categoryColor}`}>
          {template.category}
        </span>
      </div>

      <div className="flex flex-wrap gap-1">
        {template.languages.map((lang) => (
          <span key={lang} className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600 font-mono">
            {lang}
          </span>
        ))}
      </div>

      <div className="text-xs text-gray-400">{template.fields.length} fields</div>

      <div className="flex items-center justify-between pt-1 border-t border-gray-100">
        <span className="text-xs text-gray-400">
          {template.usage_count > 0 && `${template.usage_count} imports`}
          {template.is_curated && (
            <span className="ml-1 text-blue-500 font-medium">Curated</span>
          )}
        </span>
        <button
          onClick={() => onImport(template.id)}
          disabled={importing}
          className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs text-white font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {importing ? 'Importing…' : 'Import'}
        </button>
      </div>
    </div>
  )
}
