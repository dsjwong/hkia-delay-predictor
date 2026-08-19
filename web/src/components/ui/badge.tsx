import type { HTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

/** Small status / metadata pill. Status variants carry a dot so state is never colour-alone. */
const badge = cva(
  'inline-flex items-center gap-1.5 rounded-full border px-2 py-px text-[0.7rem] font-medium leading-5 whitespace-nowrap',
  {
    variants: {
      variant: {
        default: 'border-border bg-card text-ink-2',
        solid: 'border-transparent bg-elev-2 text-ink',
        ok: 'border-good/30 bg-good/10 text-good',
        warn: 'border-warning/30 bg-warning/10 text-warning',
        crit: 'border-critical/30 bg-critical/10 text-critical',
        accent: 'border-accent/30 bg-accent/10 text-accent',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badge> {
  dot?: boolean
}
export function Badge({ className, variant, dot, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badge({ variant }), className)} {...props}>
      {dot && <span className="inline-block w-1.5 h-1.5 rounded-full bg-current" aria-hidden="true" />}
      {children}
    </span>
  )
}
