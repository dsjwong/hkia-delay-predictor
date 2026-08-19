import { NavLink } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import { useMetaCtx } from '@/lib/meta-context'
import { ageMin, hm } from '@/lib/time'
import { cn } from '@/lib/utils'
import { Tooltip } from './ui/tooltip'

export const REPO = 'https://github.com/dsjwong/hkia-delay-predictor'
const NAV = [
  { to: '/', label: 'Live map' },
  { to: '/today', label: 'Today' },
  { to: '/patterns', label: 'Patterns' },
  { to: '/model', label: 'Model' },
  { to: '/about', label: 'About' },
]

export function Header() {
  const { meta } = useMetaCtx()
  const [open, setOpen] = useState(false)
  const asOf = meta.data?.data_as_of ?? null
  const age = ageMin(asOf)
  const live = age != null && age < 120
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface/90 backdrop-blur">
      <div className="mx-auto flex max-w-[1600px] items-center gap-3 px-3 sm:px-4 h-12">
        <NavLink
          to="/"
          className="flex items-center gap-2 text-ink no-underline shrink-0"
          aria-label="HKIA delay predictor — home"
        >
          <svg width="22" height="22" viewBox="0 0 64 64" aria-hidden="true">
            <rect width="64" height="64" rx="12" fill="#121c2e" />
            <path
              fill="#ffbf3d"
              d="M32 6c2.4 0 4 3.6 4 8v14l24 14v6l-24-7v13l6 5v4l-10-3-10 3v-4l6-5V41L8 48v-6l24-14V14c0-4.4 1.6-8 4-8z"
            />
          </svg>
          <span className="font-semibold tracking-[0.01em]">HKIA departures</span>
          <span className="hidden md:inline text-[0.7rem] uppercase tracking-[0.08em] text-muted ml-1">
            delay predictor · VHHH
          </span>
        </NavLink>
        <nav className="hidden md:flex items-center gap-1 ml-4" aria-label="Pages">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === '/'}
              className={({ isActive }) =>
                cn(
                  'px-2.5 py-1 rounded-md text-sm no-underline',
                  isActive ? 'bg-surface-3 text-ink' : 'text-ink-2 hover:text-ink hover:bg-surface-2',
                )
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3">
          <Tooltip
            content={
              meta.error
                ? `data snapshot failed to load: ${meta.error}`
                : `Last GitHub Actions ingest ${asOf ? hm(asOf) + ' HKT' : '—'} · last score ${hm(meta.data?.last_score)} · METAR ${hm(meta.data?.last_metar)}. Refreshed every ~30 min; LIVE turns red when the snapshot is > 2 h old.`
            }
            side="bottom"
          >
            <span
              className="flex items-center gap-2 font-mono text-[0.74rem] text-ink-2 whitespace-nowrap"
              tabIndex={0}
            >
              <span className={cn('hk-dot', !live && 'off')} aria-hidden="true" />
              <span>{meta.loading && !meta.data ? 'LOADING' : live ? 'LIVE' : 'STALE'}</span>
              <span className="hidden sm:inline">· data as of {asOf ? hm(asOf) + ' HKT' : '—'}</span>
            </span>
          </Tooltip>
          <a
            href={REPO}
            className="hidden sm:inline-flex text-ink-2 hover:text-ink"
            aria-label="Source on GitHub"
            title="Source on GitHub"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 .5a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.2c-3.3.7-4-1.4-4-1.4-.6-1.4-1.4-1.8-1.4-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1.1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0c2.3-1.5 3.3-1.2 3.3-1.2.6 1.7.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .5z" />
            </svg>
          </a>
          <button
            className="md:hidden text-ink-2 hover:text-ink"
            aria-label="Menu"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>
      {open && (
        <nav className="md:hidden border-t border-border bg-surface-2 px-3 py-2 flex flex-col" aria-label="Pages">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === '/'}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                cn('px-2 py-2 rounded-md text-sm no-underline', isActive ? 'bg-surface-3 text-ink' : 'text-ink-2')
              }
            >
              {n.label}
            </NavLink>
          ))}
          <a href={REPO} className="px-2 py-2 text-sm text-ink-2">
            Source on GitHub
          </a>
        </nav>
      )}
    </header>
  )
}
