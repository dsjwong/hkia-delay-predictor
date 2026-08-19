import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const button = cva(
  'inline-flex items-center justify-center gap-1.5 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none cursor-pointer',
  {
    variants: {
      variant: {
        default: 'bg-accent text-white hover:bg-[#2f74c9]',
        outline: 'border border-border bg-transparent text-ink-2 hover:bg-surface-3 hover:text-ink',
        ghost: 'bg-transparent text-ink-2 hover:bg-surface-3 hover:text-ink',
        pill: 'rounded-full border border-border text-ink-2 hover:bg-surface-3 hover:text-ink aria-pressed:border-accent aria-pressed:text-accent aria-pressed:bg-accent/10',
      },
      size: { sm: 'h-7 px-2.5 text-xs', md: 'h-9 px-3', icon: 'h-8 w-8' },
    },
    defaultVariants: { variant: 'default', size: 'md' },
  },
)

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof button> {}
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, type = 'button', ...props }, ref) => (
  <button ref={ref} type={type} className={cn(button({ variant, size }), className)} {...props} />
))
Button.displayName = 'Button'
