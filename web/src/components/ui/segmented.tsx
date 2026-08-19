import { Button } from './button'

/** Segmented control (shadcn Tabs-list look): one pill group, pressed item raised; arrow keys move between items. */
export function Segmented<T extends string>({
  value,
  onChange,
  options,
  label,
}: {
  value: T
  onChange: (v: T) => void
  options: { value: T; label: string }[]
  label: string
}) {
  const idx = options.findIndex((o) => o.value === value)
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
    e.preventDefault()
    const next = (idx + (e.key === 'ArrowRight' ? 1 : options.length - 1)) % options.length
    onChange(options[next].value)
    const el = (e.currentTarget as HTMLElement).querySelectorAll<HTMLButtonElement>('button')[next]
    el?.focus()
  }
  return (
    <div
      role="group"
      aria-label={label}
      onKeyDown={onKey}
      className="inline-flex items-center gap-0.5 p-0.5 rounded-lg bg-card border border-border"
    >
      {options.map((o) => (
        <Button
          key={o.value}
          variant="seg"
          size="sm"
          aria-pressed={o.value === value}
          tabIndex={o.value === value ? 0 : -1}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </Button>
      ))}
    </div>
  )
}
