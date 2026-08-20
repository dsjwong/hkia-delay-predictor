import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, TrendingUp, X } from 'lucide-react'
import { useAdsb } from '@/hooks/useAdsb'
import { beatsBaselineText } from '@/components/ReportCard'
import { useDepartures, useModel } from '@/lib/data'
import { useMetaCtx } from '@/lib/meta-context'
import { POLL_MS, PROXY_POLL_MS, RADIUS_NM } from '@/lib/adsb'
import { hm } from '@/lib/time'
import { AMBER_RAMP } from '@/lib/theme'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tooltip } from '@/components/ui/tooltip'
import { Skeleton } from '@/components/ui/skeleton'
import { PBar } from '@/components/PBar'
import { FlightCard } from '@/components/FlightCard'
import { WeatherStrip } from '@/components/WeatherStrip'
import { MapView } from './live/MapView'
import { trackAircraft, type TrackedAircraft } from './live/match'
import type { Flight } from '@/lib/types'

function useNow(ms = 1000) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), ms)
    return () => window.clearInterval(id)
  }, [ms])
  return now
}

const ROUTE_LABEL = { env: 'own relay', direct: 'direct', proxy: 'public proxy' } as const

export default function Live() {
  const { meta } = useMetaCtx()
  const today = useDepartures('today')
  const yday = useDepartures('yesterday')
  const feed = useAdsb(true)
  const model = useModel()
  const scorecard = beatsBaselineText(model.data?.live_eval)
  const now = useNow()
  const [selected, setSelected] = useState<string | null>(null)
  const [selFlight, setSelFlight] = useState<Flight | null>(null)
  const onSelect = useCallback((hex: string | null) => {
    setSelected(hex)
    if (hex) setSelFlight(null)
  }, [])

  const pool = useMemo(() => [...(yday.data?.flights ?? []), ...(today.data?.flights ?? [])], [yday.data, today.data])
  const tracked = useMemo(() => trackAircraft(feed.aircraft, pool, meta.data), [feed.aircraft, pool, meta.data])
  const matched = useMemo(
    () => tracked.filter((a) => a.flight).sort((a, b) => (a.flight!.sched_ts < b.flight!.sched_ts ? -1 : 1)),
    [tracked],
  )
  const sel = selected ? (tracked.find((a) => a.hex === selected) ?? null) : null
  const recent = useMemo(() => {
    const t = Date.now()
    return pool
      .filter((f) => f.actual_ts && t - Date.parse(f.actual_ts) >= 0 && t - Date.parse(f.actual_ts) <= 2 * 3600000)
      .sort((a, b) => (a.actual_ts! < b.actual_ts! ? 1 : -1))
      .slice(0, 12)
  }, [pool])

  const ageS = feed.fetchedAt ? Math.max(0, Math.round((now - feed.fetchedAt) / 1000)) : null
  const feedDown = !!feed.error && !feed.aircraft.length && feed.failures >= 2
  const feedTone: 'default' | 'warn' | 'crit' = feed.error ? 'crit' : feed.route === 'proxy' ? 'warn' : 'default'
  const feedText = feed.error
    ? feed.aircraft.length
      ? `feed error · last frame ${ageS}s ago`
      : 'feed unavailable · retrying'
    : feed.route
      ? `adsb.lol · ${ROUTE_LABEL[feed.route]} · ${ageS}s`
      : 'connecting to adsb.lol…'
  const loadingPool = (today.loading && !today.data) || (yday.loading && !yday.data)

  const showCard = sel || selFlight
  const closeCard = () => {
    setSelected(null)
    setSelFlight(null)
  }

  return (
    <div className="flex flex-col lg:block lg:h-[calc(100dvh-49px)] lg:overflow-hidden">
      {/* ---- map ---- */}
      <div className="hk-map-shell relative h-[58dvh] min-h-[360px] lg:h-auto lg:absolute lg:inset-0">
        <MapView aircraft={tracked} selectedHex={selected} onSelect={onSelect} className="absolute inset-0" />

        {/* top-left: stat chips */}
        <div className="absolute left-3 top-3 z-10 flex flex-wrap items-center gap-1.5 max-w-[calc(100%-24px)] lg:max-w-[calc(100%-400px)]">
          <Chip label="aircraft" value={feed.aircraft.length} sub={`${RADIUS_NM} nm`} />
          <Chip label="tracked" value={matched.length} sub="HKIA deps" tone={matched.length ? 'ok' : undefined} />
          <Tooltip
            side="bottom"
            content="Free community ADS-B feed. api.adsb.lol sends no CORS headers, so a browser can only read it through a relay: your own Cloudflare Worker (web/worker/, ADSB_PROXY_URL) polled every 8 s, or the public api.cors.lol proxy as a slow fallback (~1 request/min). Positions glide between polls by dead-reckoning on ground speed + track."
          >
            <span
              tabIndex={0}
              className={cn(
                'hk-glass inline-flex items-center gap-2 h-8 px-2.5 font-mono text-[0.72rem] whitespace-nowrap',
                feedTone === 'crit' ? 'text-critical' : feedTone === 'warn' ? 'text-warning' : 'text-ink-2',
              )}
            >
              <span
                className={cn('hk-dot', feedTone === 'crit' ? 'off' : feedTone === 'warn' ? 'idle' : '')}
                aria-hidden="true"
              />
              {feedText}
            </span>
          </Tooltip>
          {scorecard && (
            <Tooltip
              side="bottom"
              content="Rolling 7-day live evaluation: for every flight that has since departed, the last probability published before it left, scored against what actually happened, versus the airline × hour lookup table. Open the model report card for the daily series, lead-time slices, calibration and the notable calls."
            >
              <Link
                to="/model"
                className="hk-glass inline-flex items-center gap-1.5 h-8 px-2.5 text-[0.72rem] whitespace-nowrap text-accent no-underline hover:border-border-2"
              >
                <TrendingUp size={12} aria-hidden="true" />
                <span className="hk-num">{scorecard}</span>
              </Link>
            </Tooltip>
          )}
        </div>

        {/* bottom-left: legend (above the attribution) */}
        <Legend />

        {feedDown && (
          <div
            className="absolute left-3 bottom-20 z-10 max-w-[400px] hk-glass px-3.5 py-2.5 text-xs text-ink-2 leading-relaxed"
            role="status"
          >
            <b className="text-critical">Live feed unavailable from this origin.</b> api.adsb.lol (and adsb.fi /
            airplanes.live / OpenSky) send no CORS headers, and the public proxy fallback is rate-limited. Deploy{' '}
            <code className="font-mono">web/worker/adsb-proxy.js</code> to Cloudflare Workers (free) and set the
            repository variable <code className="font-mono">ADSB_PROXY_URL</code> — see the README. Retrying.
          </div>
        )}
      </div>

      {/* ---- right panel ---- */}
      <aside
        className="lg:absolute lg:top-3 lg:right-3 lg:bottom-3 lg:w-[372px] lg:z-10 flex flex-col min-h-0 hk-glass lg:rounded-card rounded-none border-x-0 lg:border-x border-t lg:border-t bg-card lg:bg-card/80"
        aria-label="Live panel"
      >
        {showCard ? (
          <div className="flex flex-col min-h-0 hk-slide">
            <div className="flex items-center gap-1 px-2 h-11 border-b border-border shrink-0">
              <Button variant="ghost" size="icon" onClick={closeCard} aria-label="Back to the list">
                <ArrowLeft size={16} />
              </Button>
              <div className="text-sm font-semibold truncate">
                {sel?.flight
                  ? `${sel.flight.flight_no} · ${sel.callsign}`
                  : sel
                    ? sel.callsign || sel.hex
                    : selFlight?.flight_no}
              </div>
              <Button variant="ghost" size="icon" className="ml-auto" onClick={closeCard} aria-label="Close">
                <X size={16} />
              </Button>
            </div>
            <div className="overflow-y-auto px-4 py-4 min-h-0">
              {sel?.flight ? (
                <FlightCard flight={sel.flight} meta={meta.data} aircraft={sel} />
              ) : sel ? (
                <Untracked a={sel} />
              ) : selFlight ? (
                <FlightCard flight={selFlight} meta={meta.data} />
              ) : null}
            </div>
          </div>
        ) : (
          <div className="overflow-y-auto min-h-0 p-3 space-y-4">
            <WeatherStrip compact />

            <section aria-labelledby="tracked-h">
              <div className="flex items-baseline justify-between mb-1.5">
                <h3 id="tracked-h" className="hk-kicker">
                  Tracked departures
                </h3>
                <span className="text-[0.7rem] text-muted hk-num">{matched.length}</span>
              </div>
              {loadingPool && !matched.length ? (
                <div className="space-y-2" role="status" aria-label="loading">
                  {[0, 1, 2].map((i) => (
                    <Skeleton key={i} className="h-8" />
                  ))}
                </div>
              ) : matched.length ? (
                <ul className="divide-y divide-border/60 rounded-lg border border-border/60 overflow-hidden bg-card/40">
                  {matched.map((a) => (
                    <li key={a.hex}>
                      <button
                        type="button"
                        onClick={() => onSelect(a.hex)}
                        aria-pressed={a.hex === selected}
                        className="w-full grid grid-cols-[44px_1fr_auto] items-center gap-2 px-2.5 py-1.5 text-left text-sm hover:bg-elev cursor-pointer"
                        title={`${a.flight!.flight_no} · ${a.airlineName} → ${a.destLabel}`}
                      >
                        <span className="hk-num text-ink-2 text-xs">{hm(a.flight!.sched_ts)}</span>
                        <span className="min-w-0 truncate">
                          <span className="font-medium">{a.flight!.flight_no}</span>
                          <span className="text-ink-2"> → {a.flight!.dest}</span>
                          <span className="text-muted text-xs">
                            {' '}
                            · {a.onGround ? 'ground' : `${Math.round(a.altFt / 100) * 100} ft`}
                          </span>
                        </span>
                        <PBar p={a.flight!.p} width={44} />
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-muted leading-relaxed">
                  No HKIA departure is inside the {RADIUS_NM} nm ring with a matching callsign right now. Departures
                  leave the ring ~15 min after take-off, so this list is usually short.
                </p>
              )}
            </section>

            <section aria-labelledby="recent-h">
              <div className="flex items-baseline justify-between mb-1.5">
                <h3 id="recent-h" className="hk-kicker">
                  Recent departures
                </h3>
                <span className="text-[0.7rem] text-muted">last 2 h · snapshot</span>
              </div>
              {loadingPool ? (
                <div className="space-y-2" role="status" aria-label="loading">
                  {[0, 1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-7" />
                  ))}
                </div>
              ) : recent.length ? (
                <ul className="divide-y divide-border/60 rounded-lg border border-border/60 overflow-hidden bg-card/40">
                  {recent.map((f) => (
                    <li key={f.flight_no + f.sched_ts}>
                      <button
                        type="button"
                        onClick={() => {
                          setSelected(null)
                          setSelFlight(f)
                        }}
                        className="w-full grid grid-cols-[44px_1fr_40px_auto] items-center gap-2 px-2.5 py-1.5 text-left text-sm hover:bg-elev cursor-pointer"
                        title="open the flight card"
                      >
                        <span className="hk-num text-ink-2 text-xs">{hm(f.actual_ts)}</span>
                        <span className="min-w-0 truncate">
                          <span className="font-medium">{f.flight_no}</span>
                          <span className="text-ink-2"> → {f.dest}</span>
                        </span>
                        <span
                          className={cn(
                            'hk-num text-xs text-right',
                            f.delay_min != null && f.delay_min > 15 ? 'text-warning' : 'text-ink-2',
                          )}
                        >
                          {f.delay_min == null ? '—' : (f.delay_min > 0 ? '+' : '') + f.delay_min}
                        </span>
                        <PBar p={f.p} width={36} />
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-muted">No departures in the last 2 h in the latest snapshot.</p>
              )}
            </section>

            <p className="text-[0.68rem] text-muted leading-relaxed">
              Match = ICAO airline code + flight number (CPA261 ↔ CX 261). Colour = latest P(delay &gt; 15) of that
              flight; departed flights keep their last score. Click a plane or a row for the flight card. Feed polled
              every {feed.route === 'proxy' ? PROXY_POLL_MS / 1000 : POLL_MS / 1000} s.
            </p>
          </div>
        )}
      </aside>
    </div>
  )
}

function Chip({ label, value, sub, tone }: { label: string; value: number | string; sub?: string; tone?: 'ok' }) {
  return (
    <span className="hk-glass inline-flex items-baseline gap-1.5 h-8 px-2.5 text-xs whitespace-nowrap">
      <span className={cn('text-base font-semibold tracking-tight hk-num', tone === 'ok' ? 'text-good' : 'text-ink')}>
        {value}
      </span>
      <span className="text-ink-2">{label}</span>
      {sub && <span className="text-muted">· {sub}</span>}
    </span>
  )
}

function Untracked({ a }: { a: TrackedAircraft }) {
  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center gap-2">
        <span className="text-xl font-semibold tracking-tight font-mono">{a.callsign || a.hex}</span>
        <Badge>not an HKIA departure</Badge>
      </div>
      <div className="text-ink-2 text-xs leading-relaxed">
        No matching flight number in today's or yesterday's departure schedule — an arrival, overflight or general
        aviation.
      </div>
      <dl className="grid grid-cols-2 gap-y-1.5 text-xs">
        <dt className="text-muted">registration / type</dt>
        <dd className="hk-num">
          {a.reg || '—'} / {a.type || '—'}
        </dd>
        <dt className="text-muted">altitude</dt>
        <dd className="hk-num">{a.onGround ? 'on ground' : `${Math.round(a.altFt).toLocaleString()} ft`}</dd>
        <dt className="text-muted">ground speed / track</dt>
        <dd className="hk-num">
          {a.gsKt == null ? '—' : Math.round(a.gsKt) + ' kt'} /{' '}
          {a.trackDeg == null ? '—' : Math.round(a.trackDeg) + '°'}
        </dd>
        <dt className="text-muted">distance from HKIA</dt>
        <dd className="hk-num">{a.distNm.toFixed(0)} nm</dd>
      </dl>
    </div>
  )
}

function Legend() {
  return (
    <div
      className="absolute left-3 bottom-9 z-10 hk-glass px-3 py-2 hidden sm:flex flex-col gap-1 text-[0.7rem] text-ink-2"
      aria-label="Map legend"
    >
      <span className="inline-flex items-center gap-2">
        <span
          className="inline-block w-12 h-1.5 rounded-full"
          style={{ background: `linear-gradient(90deg, ${AMBER_RAMP.join(',')})` }}
          aria-hidden="true"
        />
        departure · P(delay &gt; 15) 0 → 100 %
      </span>
      <span className="inline-flex items-center gap-2">
        <span className="inline-block w-12 h-1.5 rounded-full bg-ink" aria-hidden="true" />
        departure, not scored
      </span>
      <span className="inline-flex items-center gap-2">
        <span
          className="inline-block w-12 h-1.5 rounded-full"
          style={{ background: 'linear-gradient(90deg,#71717a,#f4f4f5)' }}
          aria-hidden="true"
        />
        other traffic · altitude low → high
      </span>
      <span className="text-muted">rings 50 / 100 nm · data adsb.lol</span>
    </div>
  )
}
