import { amberHex } from '@/lib/theme'
import { pct } from '@/lib/time'
import { cn } from '@/lib/utils'

/** P(delay > 15) as a thin bar on the single-hue amber ramp + the number (never colour alone). */
export function PBar({
  p,
  className,
  width = 64,
}: {
  p: number | null | undefined
  className?: string
  width?: number
}) {
  if (p == null) return <span className={cn('text-muted text-xs', className)}>—</span>
  return (
    <span className={cn('inline-flex items-center gap-2 hk-num', className)} title={`P(delay > 15 min) = ${pct(p)}`}>
      <span className="h-[6px] rounded-full bg-surface-3 overflow-hidden" style={{ width }} aria-hidden="true">
        <span
          className="block h-full rounded-full"
          style={{ width: `${Math.round(p * 100)}%`, background: amberHex(p) }}
        />
      </span>
      <span className="text-xs text-ink-2 w-9 text-right">{pct(p)}</span>
    </span>
  )
}
