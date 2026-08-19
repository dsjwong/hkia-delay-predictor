import { cn } from '@/lib/utils'

/** Skeleton block for an async region. Pass a height class; width defaults to full. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('hk-skeleton h-4 w-full', className)} aria-hidden="true" />
}

/** A whole card's worth of skeleton: title line + body block. */
export function SkeletonCard({ className, body = 'h-48' }: { className?: string; body?: string }) {
  return (
    <div className={cn('hk-card p-4 space-y-3', className)} role="status" aria-label="loading">
      <Skeleton className="h-3.5 w-40" />
      <Skeleton className={cn('w-full', body)} />
    </div>
  )
}

/** Skeleton table rows. */
export function SkeletonRows({ rows = 6, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="p-3 space-y-2" role="status" aria-label="loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex gap-3">
          {Array.from({ length: cols }, (_, j) => (
            <Skeleton key={j} className={cn('h-3.5', j === 0 ? 'w-12' : j === 1 ? 'w-20' : 'flex-1')} />
          ))}
        </div>
      ))}
    </div>
  )
}
