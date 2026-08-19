import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Tooltip } from './tooltip'
import { Info } from 'lucide-react'

/** Stat tile: kicker label, hero number (proportional figures), one line of context. */
export function Tile({ label, value, sub, hint, className, tone }: { label: string; value: ReactNode; sub?: ReactNode; hint?: ReactNode; className?: string; tone?: 'warn' | 'crit' | 'ok' }) {
  return (
    <div className={cn('hk-card px-3.5 py-2.5 min-w-0', className)}>
      <div className="flex items-center gap-1.5 hk-kicker">
        <span className="truncate">{label}</span>
        {hint && (
          <Tooltip content={hint}>
            <Info size={12} className="text-muted/80 shrink-0" aria-label="about this number" tabIndex={0} />
          </Tooltip>
        )}
      </div>
      <div className={cn('mt-0.5 text-[1.45rem] leading-8 font-semibold text-ink', tone === 'warn' && 'text-warning', tone === 'crit' && 'text-critical', tone === 'ok' && 'text-good')}>{value}</div>
      {sub && <div className="text-[0.74rem] text-ink-2 truncate">{sub}</div>}
    </div>
  )
}
