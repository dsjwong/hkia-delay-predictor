import { useCallback, useMemo, useState } from 'react'
import { useAdsb } from '@/hooks/useAdsb'
import { useDepartures } from '@/lib/data'
import { useMetaCtx } from '@/lib/meta-context'
import { POLL_MS, PROXY_POLL_MS, RADIUS_NM } from '@/lib/adsb'
import { hms, hm } from '@/lib/time'
import { AMBER_RAMP } from '@/lib/theme'
import { Badge } from '@/components/ui/badge'
import { Sheet } from '@/components/ui/sheet'
import { Tile } from '@/components/ui/tile'
import { Tooltip } from '@/components/ui/tooltip'
import { PBar } from '@/components/PBar'
import { FlightCard } from '@/components/FlightCard'
import { WeatherStrip } from '@/components/WeatherStrip'
import { MapView } from './live/MapView'
import { trackAircraft } from './live/match'
import type { Flight } from '@/lib/types'

export default function Live() {
  const { meta } = useMetaCtx()
  const today = useDepartures('today')
  const yday = useDepartures('yesterday')
  const feed = useAdsb(true)
  const [selected, setSelected] = useState<string | null>(null)
  const onSelect = useCallback((hex: string | null) => setSelected(hex), [])

  const pool = useMemo(() => [...(yday.data?.flights ?? []), ...(today.data?.flights ?? [])], [yday.data, today.data])
  const tracked = useMemo(() => trackAircraft(feed.aircraft, pool, meta.data), [feed.aircraft, pool, meta.data])
  const matched = useMemo(() => tracked.filter((a) => a.flight).sort((a, b) => (a.flight!.sched_ts < b.flight!.sched_ts ? -1 : 1)), [tracked])
  const sel = selected ? tracked.find((a) => a.hex === selected) ?? null : null
  const nRecent = useMemo(() => {
    const now = Date.now()
    return pool.filter((f) => f.actual_ts && now - Date.parse(f.actual_ts) >= 0 && now - Date.parse(f.actual_ts) <= 45 * 60000).length
  }, [pool])

  const feedBadge = feed.error
    ? feed.aircraft.length
      ? { v: 'crit' as const, t: `feed unavailable — showing last good frame (${feed.error})` }
      : { v: 'crit' as const, t: `feed unavailable (${feed.error}) — retrying with backoff` }
    : feed.route === 'proxy'
      ? { v: 'warn' as const, t: `adsb.lol ${feed.fetchedAt ? hms(feed.fetchedAt) : '—'} HKT · via public CORS proxy, every ${PROXY_POLL_MS / 1000} s` }
      : { v: 'default' as const, t: `adsb.lol ${feed.fetchedAt ? hms(feed.fetchedAt) : '—'} HKT · every ${POLL_MS / 1000} s` }
  const feedDown = !!feed.error && !feed.aircraft.length && feed.failures >= 2
  const recent = useMemo(() => {
    const now = Date.now()
    return pool
      .filter((f) => f.actual_ts && now - Date.parse(f.actual_ts) >= 0 && now - Date.parse(f.actual_ts) <= 2 * 3600000)
      .sort((a, b) => (a.actual_ts! < b.actual_ts! ? 1 : -1))
      .slice(0, 12)
  }, [pool])
  const [selFlight, setSelFlight] = useState<Flight | null>(null)

  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(0,2.5fr)_minmax(300px,1.1fr)]">
      <section className="min-w-0">
        <div className="flex flex-wrap items-center gap-1.5 mb-2">
          <Badge>
            {feed.aircraft.length} aircraft in {RADIUS_NM} nm
          </Badge>
          <Badge variant={matched.length ? 'ok' : 'default'}>{matched.length} HKIA departures tracked</Badge>
          <Tooltip
            content="Free community ADS-B feed. api.adsb.lol sends no CORS headers, so a browser can only read it through a relay: a 20-line Cloudflare Worker (web/worker/, set ADSB_PROXY_URL) polled every 8 s, or the public api.cors.lol proxy as a slow fallback (~1 request/min). Positions glide between polls by dead-reckoning on ground speed + track."
            side="bottom"
          >
            <Badge variant={feedBadge.v} tabIndex={0}>
              {feedBadge.t}
            </Badge>
          </Tooltip>
        </div>
        <div className="relative hk-card overflow-hidden h-[52vh] min-h-[360px] lg:h-[calc(100vh-190px)] lg:min-h-[520px]">
          <MapView aircraft={tracked} selectedHex={selected} onSelect={onSelect} className="absolute inset-0" />
          {feedDown && (
            <div className="absolute left-3 bottom-3 max-w-[420px] hk-card px-3 py-2 text-xs text-ink-2 z-10" role="status">
              <b className="text-critical">Live feed unavailable from this origin.</b> api.adsb.lol (and adsb.fi / airplanes.live / OpenSky) send no CORS headers, and the public
              proxy fallback is rate-limited. The map still works with a tiny relay: deploy <code className="font-mono">web/worker/adsb-proxy.js</code> to Cloudflare Workers
              (free) and set the repository variable <code className="font-mono">ADSB_PROXY_URL</code> — see the README. Retrying in the background.
            </div>
          )}
          <Sheet open={!!sel} onClose={() => setSelected(null)} inline title={sel?.flight ? `${sel.flight.flight_no} · ${sel.callsign}` : sel?.callsign || 'aircraft'}>
            {sel?.flight ? (
              <FlightCard flight={sel.flight} meta={meta.data} aircraft={sel} />
            ) : sel ? (
              <div className="space-y-2 text-sm">
                <div className="text-ink-2">Not an HKIA departure we track (no matching flight number in today's or yesterday's schedule, or it is an arrival / overflight).</div>
                <dl className="grid grid-cols-2 gap-y-1 text-xs">
                  <dt className="text-muted">registration / type</dt>
                  <dd className="hk-num">
                    {sel.reg || '—'} / {sel.type || '—'}
                  </dd>
                  <dt className="text-muted">altitude</dt>
                  <dd className="hk-num">{sel.onGround ? 'on ground' : `${Math.round(sel.altFt).toLocaleString()} ft`}</dd>
                  <dt className="text-muted">ground speed / track</dt>
                  <dd className="hk-num">
                    {sel.gsKt == null ? '—' : Math.round(sel.gsKt) + ' kt'} / {sel.trackDeg == null ? '—' : Math.round(sel.trackDeg) + '°'}
                  </dd>
                  <dt className="text-muted">distance from HKIA</dt>
                  <dd className="hk-num">{sel.distNm.toFixed(0)} nm</dd>
                </dl>
              </div>
            ) : null}
          </Sheet>
        </div>
        <Legend />
      </section>

      <aside className="min-w-0 space-y-3" aria-label="Live panel">
        <div className="grid grid-cols-3 gap-2">
          <Tile label="In range" value={feed.aircraft.length} sub={`within ${RADIUS_NM} nm`} />
          <Tile label="Tracked" value={matched.length} sub="HKIA departures" hint="Aircraft whose callsign matches a flight number in today's / yesterday's HKIA departure schedule (CPA261 ↔ CX 261)." />
          <Tile label="Departed" value={nRecent} sub="last 45 min" hint="Flights with an actual departure time in the last 45 min according to the latest snapshot." />
        </div>
        <WeatherStrip compact />
        <div>
          <h3 className="hk-kicker mb-1.5">Tracked departures</h3>
          {matched.length ? (
            <div className="hk-card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left hk-kicker border-b border-border">
                    <th className="px-2.5 py-1.5 font-normal">Sched</th>
                    <th className="px-2 py-1.5 font-normal">Flight</th>
                    <th className="px-2 py-1.5 font-normal">To</th>
                    <th className="px-2 py-1.5 font-normal">P(&gt;15)</th>
                  </tr>
                </thead>
                <tbody>
                  {matched.map((a) => (
                    <tr
                      key={a.hex}
                      tabIndex={0}
                      role="button"
                      aria-pressed={a.hex === selected}
                      onClick={() => setSelected(a.hex)}
                      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), setSelected(a.hex))}
                      className={`cursor-pointer border-b border-border/60 last:border-0 hover:bg-surface-3 ${a.hex === selected ? 'bg-surface-3' : ''}`}
                      title={`${a.flight!.flight_no} · ${a.airlineName} → ${a.destLabel} · click for the flight card`}
                    >
                      <td className="px-2.5 py-1.5 hk-num text-ink-2">{hm(a.flight!.sched_ts)}</td>
                      <td className="px-2 py-1.5 font-medium">{a.flight!.flight_no}</td>
                      <td className="px-2 py-1.5 text-ink-2">{a.flight!.dest}</td>
                      <td className="px-2 py-1.5">
                        <PBar p={a.flight!.p} width={48} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-muted">
              No HKIA departure of the last few hours is currently inside the {RADIUS_NM} nm ring with a matching callsign. Departures leave the ring ~15 min after
              take-off, so this list is usually short.
            </p>
          )}
          <p className="text-[0.7rem] text-muted mt-1.5">
            Match = ICAO airline code + flight number (CPA261 ↔ CX 261). Colour = latest P(delay &gt; 15) of that flight; departed flights keep their last score.
            Click a plane or a row for the flight card.
          </p>
        </div>
        <div>
          <h3 className="hk-kicker mb-1.5">Recent departures (snapshot, last 2 h)</h3>
          {recent.length ? (
            <div className="hk-card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left hk-kicker border-b border-border">
                    <th className="px-2.5 py-1.5 font-normal">Actual</th>
                    <th className="px-2 py-1.5 font-normal">Flight</th>
                    <th className="px-2 py-1.5 font-normal">To</th>
                    <th className="px-2 py-1.5 font-normal">Delay</th>
                    <th className="px-2 py-1.5 font-normal">P(&gt;15)</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((f) => (
                    <tr
                      key={f.flight_no + f.sched_ts}
                      tabIndex={0}
                      role="button"
                      onClick={() => setSelFlight(f)}
                      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), setSelFlight(f))}
                      className="cursor-pointer border-b border-border/60 last:border-0 hover:bg-surface-3"
                      title="open the flight card"
                    >
                      <td className="px-2.5 py-1 hk-num text-ink-2">{hm(f.actual_ts)}</td>
                      <td className="px-2 py-1 font-medium">{f.flight_no}</td>
                      <td className="px-2 py-1 text-ink-2">{f.dest}</td>
                      <td className="px-2 py-1 hk-num text-ink-2">{f.delay_min == null ? '—' : (f.delay_min > 0 ? '+' : '') + f.delay_min}</td>
                      <td className="px-2 py-1">
                        <PBar p={f.p} width={40} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-muted">No departures in the last 2 h in the latest snapshot.</p>
          )}
        </div>
        <Sheet open={!!selFlight} onClose={() => setSelFlight(null)} title={selFlight ? selFlight.flight_no : ''}>
          {selFlight && <FlightCard flight={selFlight} meta={meta.data} />}
        </Sheet>
      </aside>
    </div>
  )
}

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5 text-[0.72rem] text-ink-2" aria-label="Map legend">
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-block w-[70px] h-2 rounded-full" style={{ background: `linear-gradient(90deg, ${AMBER_RAMP.join(',')})` }} aria-hidden="true" />
        HKIA departure · P(delay &gt; 15) 0 → 100 %
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-block w-2.5 h-2.5 rounded-full bg-accent" aria-hidden="true" /> tracked, not scored
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-block w-[70px] h-2 rounded-full" style={{ background: 'linear-gradient(90deg,#78829a,#ecf0f6)' }} aria-hidden="true" /> other traffic · altitude low → high
      </span>
      <span className="text-muted">rings: 50 / 100 nm · data: adsb.lol</span>
    </div>
  )
}
