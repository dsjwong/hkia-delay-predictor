import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Tooltip } from './tooltip'
import { Info } from 'lucide-react'

/** KPI tile: kicker label, hero number (proportional figures, tight tracking), one line of context. */
export function Tile({
  label,
  value,
  sub,
  hint,
  className,
  tone,
  loading,
}: {
  label: string
  value: ReactNode
  sub?: ReactNode
  hint?: ReactNode
  className?: string
  tone?: 'warn' | 'crit' | 'ok' | 'accent'
  loading?: boolean
}) {
  return (
    <div className={cn('hk-card px-4 py-3 min-w-0', className)}>
      <div className="flex items-center gap-1.5 hk-kicker">
        <span className="truncate">{label}</span>
        {hint && (
          <Tooltip content={hint}>
            <Info size={12} className="text-muted shrink-0" aria-label="about this number" tabIndex={0} />
          </Tooltip>
        )}
      </div>
      {loading ? (
        <div className="hk-skeleton h-7 w-20 mt-1.5" aria-hidden="true" />
      ) : (
        <div
          className={cn(
            'mt-1 text-[1.6rem] leading-8 font-semibold tracking-[-0.02em] text-ink',
            tone === 'warn' && 'text-warning',
            tone === 'crit' && 'text-critical',
            tone === 'ok' && 'text-good',
            tone === 'accent' && 'text-accent',
          )}
        >
          {value}
        </div>
      )}
      {sub && <div className="text-xs text-ink-2 truncate mt-0.5">{loading ? ' ' : sub}</div>}
    </div>
  )
}
