import { useEffect, useRef, type ReactNode } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from './button'

export interface SheetProps {
  open: boolean
  onClose: () => void
  title?: ReactNode
  children: ReactNode
  className?: string
  /** render inline (inside a relative parent) instead of fixed to the viewport */
  inline?: boolean
}

/** Right-hand drawer: Esc closes, focus moves into the panel, click on the scrim closes. */
export function Sheet({ open, onClose, title, children, className, inline }: SheetProps) {
  const panel = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    const prev = document.activeElement as HTMLElement | null
    panel.current?.focus()
    return () => {
      window.removeEventListener('keydown', onKey)
      prev?.focus?.()
    }
  }, [open, onClose])
  if (!open) return null
  return (
    <div className={cn(inline ? 'absolute inset-0 z-20' : 'fixed inset-0 z-50', 'flex justify-end')} role="presentation">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
      <div
        ref={panel}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : 'details'}
        className={cn(
          'relative h-full w-full max-w-[420px] overflow-y-auto bg-surface-2 border-l border-border shadow-2xl outline-none',
          'animate-[hkslide_.18s_ease-out]',
          className,
        )}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between gap-2 bg-surface-2/95 backdrop-blur px-4 py-2.5 border-b border-border">
          <div className="min-w-0 text-sm font-semibold text-ink">{title}</div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
            <X size={16} />
          </Button>
        </div>
        <div className="px-4 py-3">{children}</div>
      </div>
      <style>{`@keyframes hkslide{from{transform:translateX(12px);opacity:.6}to{transform:none;opacity:1}}`}</style>
    </div>
  )
}
