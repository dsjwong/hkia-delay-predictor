import { NavLink } from 'react-router-dom'
import { Activity, BarChart3, CalendarDays, Info, Map as MapIcon, Wind } from 'lucide-react'
import { useMetaCtx } from '@/lib/meta-context'
import { ageMin, hm } from '@/lib/time'
import { cn } from '@/lib/utils'
import { Tooltip } from './ui/tooltip'

export const REPO = 'https://github.com/dsjwong/hkia-delay-predictor'
const NAV = [
  { to: '/', label: 'Live map', icon: MapIcon },
  { to: '/today', label: 'Today', icon: CalendarDays },
  { to: '/patterns', label: 'Patterns', icon: BarChart3 },
  { to: '/model', label: 'Model', icon: Activity },
  { to: '/typhoon', label: 'Case study', icon: Wind },
  { to: '/about', label: 'About', icon: Info },
]

function Wordmark() {
  return (
    <NavLink
      to="/"
      className="flex items-center gap-2 text-ink no-underline shrink-0 hover:opacity-90"
      aria-label="HKIA delay predictor — home"
    >
      <svg width="22" height="22" viewBox="0 0 64 64" aria-hidden="true">
        <rect width="64" height="64" rx="14" fill="#27272a" />
        <path
          fill="#fafafa"
          d="M32 6c2.4 0 4 3.6 4 8v14l24 14v6l-24-7v13l6 5v4l-10-3-10 3v-4l6-5V41L8 48v-6l24-14V14c0-4.4 1.6-8 4-8z"
        />
      </svg>
      <span className="font-semibold tracking-tight text-[0.95rem]">HKIA departures</span>
      <span className="hidden lg:inline text-[0.7rem] uppercase tracking-[0.06em] text-muted ml-1">
        delay predictor · VHHH
      </span>
    </NavLink>
  )
}

function LivePill() {
  const { meta } = useMetaCtx()
  const asOf = meta.data?.data_as_of ?? null
  const age = ageMin(asOf)
  const live = age != null && age < 120
  const loading = meta.loading && !meta.data
  return (
    <Tooltip
      content={
        meta.error
          ? `data snapshot failed to load: ${meta.error}`
          : `Last GitHub Actions ingest ${asOf ? hm(asOf) + ' HKT' : '—'} · last score ${hm(meta.data?.last_score)} · METAR ${hm(meta.data?.last_metar)}. Refreshed every ~30 min; turns STALE when the snapshot is > 2 h old.`
      }
      side="bottom"
    >
      <span
        className="inline-flex items-center gap-2 h-7 px-2.5 rounded-full border border-border bg-card font-mono text-[0.72rem] text-ink-2 whitespace-nowrap"
        tabIndex={0}
      >
        <span className={cn('hk-dot', loading ? 'idle' : !live && 'off')} aria-hidden="true" />
        <span className={cn('font-semibold', live && !loading ? 'text-ink' : loading ? 'text-ink-2' : 'text-critical')}>
          {loading ? 'LOADING' : live ? 'LIVE' : 'STALE'}
        </span>
        <span className="hidden sm:inline text-muted">{asOf ? hm(asOf) + ' HKT' : '—'}</span>
      </span>
    </Tooltip>
  )
}

function GitHub() {
  return (
    <a
      href={REPO}
      className="inline-flex items-center justify-center h-8 w-8 rounded-md text-ink-2 hover:text-ink hover:bg-elev no-underline"
      aria-label="Source on GitHub"
      title="Source on GitHub"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M12 .5a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.2c-3.3.7-4-1.4-4-1.4-.6-1.4-1.4-1.8-1.4-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1.1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0c2.3-1.5 3.3-1.2 3.3-1.2.6 1.7.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .5z" />
      </svg>
    </a>
  )
}

/** Slim top bar: wordmark, quiet tab nav (desktop), LIVE pill + GitHub. On mobile the nav moves to BottomTabs. */
export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-bg/85 backdrop-blur-md">
      <div className="flex items-center gap-3 px-3 sm:px-4 h-12">
        <Wordmark />
        <nav className="hidden md:flex items-center gap-0.5 ml-4" aria-label="Pages">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === '/'}
              className={({ isActive }) =>
                cn(
                  'relative h-12 inline-flex items-center px-3 text-sm no-underline transition-colors',
                  isActive ? 'text-ink' : 'text-ink-2 hover:text-ink',
                  isActive && 'after:absolute after:left-2 after:right-2 after:-bottom-px after:h-px after:bg-ink',
                )
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <LivePill />
          <GitHub />
        </div>
      </div>
    </header>
  )
}

/** Mobile bottom tab bar (hidden on md+). */
export function BottomTabs() {
  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-30 border-t border-border bg-bg/90 backdrop-blur-md pb-[env(safe-area-inset-bottom)]"
      aria-label="Pages"
    >
      <div className="grid grid-cols-6 h-14">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.to === '/'}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center justify-center gap-0.5 text-[0.65rem] no-underline',
                isActive ? 'text-ink' : 'text-muted',
              )
            }
          >
            <n.icon size={18} aria-hidden="true" />
            {n.label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
