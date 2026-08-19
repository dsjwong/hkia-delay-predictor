import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Inbox, AlertTriangle } from 'lucide-react'

/** Empty / error state for an async block: icon, one line, optional detail + action. */
export function Empty({
  title,
  detail,
  action,
  tone = 'empty',
  className,
}: {
  title: ReactNode
  detail?: ReactNode
  action?: ReactNode
  tone?: 'empty' | 'error'
  className?: string
}) {
  const Icon = tone === 'error' ? AlertTriangle : Inbox
  return (
    <div
      className={cn('flex flex-col items-center justify-center text-center gap-1.5 px-4 py-8', className)}
      role={tone === 'error' ? 'alert' : 'status'}
    >
      <Icon size={18} className={tone === 'error' ? 'text-critical' : 'text-muted'} aria-hidden="true" />
      <div className="text-sm text-ink-2">{title}</div>
      {detail && <div className="text-xs text-muted max-w-[420px] leading-relaxed">{detail}</div>}
      {action && <div className="mt-1">{action}</div>}
    </div>
  )
}
