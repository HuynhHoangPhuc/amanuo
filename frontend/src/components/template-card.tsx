/** Template marketplace card — displays a single schema template with import action. */

import type { SchemaTemplate } from '#/lib/types'

interface TemplateCardProps {
  template: SchemaTemplate
  onImport: (id: string) => void
  importing: boolean
}

const CATEGORY_COLORS: Record<string, string> = {
  invoice: 'bg-primary/10 text-primary',
  receipt: 'bg-green-500/10 text-green-700',
  identity: 'bg-purple-500/10 text-purple-700',
  medical: 'bg-red-500/10 text-red-700',
  other: 'bg-muted text-foreground',
}

export function TemplateCard({ template, onImport, importing }: TemplateCardProps) {
  const categoryColor = CATEGORY_COLORS[template.category] ?? CATEGORY_COLORS.other

  return (
    <div className="rounded-md border border-border bg-card p-4 flex flex-col gap-3 hover:bg-accent/50 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-foreground leading-tight">{template.name}</h3>
          {template.description && (
            <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{template.description}</p>
          )}
        </div>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${categoryColor}`}>
          {template.category}
        </span>
      </div>

      <div className="flex flex-wrap gap-1">
        {template.languages.map((lang) => (
          <span key={lang} className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground font-mono">
            {lang}
          </span>
        ))}
      </div>

      <div className="text-xs text-muted-foreground/70">{template.fields.length} fields</div>

      <div className="flex items-center justify-between pt-1 border-t border-border/50">
        <span className="text-xs text-muted-foreground/70">
          {template.usage_count > 0 && `${template.usage_count} imports`}
          {template.is_curated && (
            <span className="ml-1 text-primary font-medium">Curated</span>
          )}
        </span>
        <button
          onClick={() => onImport(template.id)}
          disabled={importing}
          className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {importing ? 'Importing…' : 'Import'}
        </button>
      </div>
    </div>
  )
}
