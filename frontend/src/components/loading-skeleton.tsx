/** Reusable loading skeleton placeholders — uses shadcn Skeleton. */

import { Skeleton } from '#/components/ui/skeleton'

export { Skeleton }

export function CardSkeleton() {
  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-8 w-1/2" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  )
}

export function TableRowSkeleton({ cols = 4 }: { cols?: number }) {
  return (
    <tr className="h-9">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-3 py-0">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  )
}

export function PageSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-6 w-48" />
      <div className="grid grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
      <div className="rounded-lg border border-border bg-card">
        <div className="px-3 py-2 border-b border-border">
          <Skeleton className="h-4 w-32" />
        </div>
        <table className="w-full">
          <tbody>
            {Array.from({ length: 5 }).map((_, i) => (
              <TableRowSkeleton key={i} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
