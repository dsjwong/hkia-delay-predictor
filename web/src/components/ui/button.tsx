import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const button = cva(
  'inline-flex items-center justify-center gap-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-colors disabled:opacity-50 disabled:pointer-events-none cursor-pointer select-none',
  {
    variants: {
      variant: {
        default: 'bg-ink text-bg hover:bg-ink/90',
        outline: 'border border-border bg-transparent text-ink-2 hover:bg-elev hover:text-ink hover:border-border-2',
        ghost: 'bg-transparent text-ink-2 hover:bg-elev hover:text-ink',
        /** segmented-control item: quiet until pressed */
        seg: 'rounded-[6px] text-ink-2 hover:text-ink aria-pressed:bg-elev-2 aria-pressed:text-ink aria-pressed:shadow-[inset_0_0_0_1px_#3f3f46]',
        link: 'text-ink underline underline-offset-2 decoration-border-2 hover:decoration-ink-2 h-auto px-0',
      },
      size: { sm: 'h-7 px-2.5 text-xs', md: 'h-9 px-3', icon: 'h-8 w-8' },
    },
    defaultVariants: { variant: 'default', size: 'md' },
  },
)

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof button> {}
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type = 'button', ...props }, ref) => (
    <button ref={ref} type={type} className={cn(button({ variant, size }), className)} {...props} />
  ),
)
Button.displayName = 'Button'
