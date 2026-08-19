import type { HTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badge = cva('inline-flex items-center gap-1 rounded-full border px-2 py-[1px] text-[0.7rem] leading-5 whitespace-nowrap', {
  variants: {
    variant: {
      default: 'border-border text-ink-2',
      ok: 'border-good text-good',
      warn: 'border-warning text-warning',
      crit: 'border-critical text-critical',
      accent: 'border-accent text-accent',
      solid: 'border-transparent bg-surface-3 text-ink',
    },
  },
  defaultVariants: { variant: 'default' },
})

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badge> {}
export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badge({ variant }), className)} {...props} />
}
