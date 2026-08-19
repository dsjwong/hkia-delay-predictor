import { useId, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

/** Hover/focus tooltip (no portal; keep the trigger inline). Keyboard users see it on focus. */
export function Tooltip({
  content,
  children,
  className,
  side = 'top',
}: {
  content: ReactNode
  children: ReactNode
  className?: string
  side?: 'top' | 'bottom'
}) {
  const [open, setOpen] = useState(false)
  const id = useId()
  return (
    <span
      className={cn('relative inline-flex', className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      aria-describedby={open ? id : undefined}
    >
      {children}
      {open && (
        <span
          role="tooltip"
          id={id}
          className={cn(
            'pointer-events-none absolute left-1/2 z-40 w-max max-w-[280px] -translate-x-1/2 rounded-md border border-border bg-surface-3 px-2.5 py-1.5 text-xs text-ink shadow-lg',
            side === 'top' ? 'bottom-full mb-1.5' : 'top-full mt-1.5',
          )}
        >
          {content}
        </span>
      )}
    </span>
  )
}
