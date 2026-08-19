import { Badge } from './ui/badge'
import { PBar } from './PBar'
import { Sparkline } from './Sparkline'
import { airlineName, destLabel } from '@/lib/data'
import type { Flight, Meta } from '@/lib/types'
import { dt, hm, num, signed } from '@/lib/time'
import type { Aircraft } from '@/lib/adsb'

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1 border-b border-border/60 last:border-0">
      <span className="text-xs text-muted">{k}</span>
      <span className="text-sm text-ink text-right hk-num">{v}</span>
    </div>
  )
}

export function statusBadge(f: Flight) {
  if (f.status === 'cancelled') return <Badge variant="crit">cancelled</Badge>
  if (f.status === 'departed') return <Badge variant="ok">departed {hm(f.actual_ts)}</Badge>
  return <Badge variant="accent">scheduled{f.est_ts ? ` · est ${hm(f.est_ts)}` : ''}</Badge>
}

/** Flight details: prediction, schedule vs actual, destination, prediction history sparkline, and (on the live map) the aircraft. */
export function FlightCard({ flight: f, meta, aircraft }: { flight: Flight; meta: Meta | null; aircraft?: Aircraft | null }) {
  const a = meta?.airports[f.dest]
  const hit = f.delay_min != null && f.p != null ? (f.p >= 0.5) === (f.delay_min > 15) : null
  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-lg font-semibold">{f.flight_no}</span>
          <span className="text-sm text-ink-2">{airlineName(meta, f.airline)}</span>
          {statusBadge(f)}
        </div>
        <div className="text-sm text-ink-2 mt-0.5">
          → {destLabel(meta, f.dest)}
          {a?.country ? `, ${a.country}` : ''}
          {f.dest_all && f.dest_all !== f.dest ? ` (via ${f.dest_all})` : ''}
        </div>
      </div>

      <section aria-labelledby="fc-pred">
        <h4 id="fc-pred" className="hk-kicker mb-1">
          Prediction
        </h4>
        {f.p == null ? (
          <div className="text-sm text-muted">Not scored yet — the cron scores not-yet-departed flights every 30 min.</div>
        ) : (
          <div className="hk-card px-3 py-2.5 space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-muted">P(delay &gt; 15 min)</span>
              <PBar p={f.p} width={90} />
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-muted">predicted delay</span>
              <span className="text-sm hk-num">{f.pred_min == null ? '—' : `${Math.round(f.pred_min)} min`}</span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-muted">last scored</span>
              <span className="text-xs text-ink-2">{dt(f.scored_at)}</span>
            </div>
            {f.delay_min != null && (
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-muted">actual delay</span>
                <span className="text-sm hk-num">
                  {signed(f.delay_min)} min{' '}
                  {hit != null && (
                    <Badge variant={hit ? 'ok' : 'warn'} className="ml-1">
                      {hit ? 'hit' : 'miss'} at P ≥ 50 %
                    </Badge>
                  )}
                </span>
              </div>
            )}
          </div>
        )}
        {f.history && f.history.length > 1 && (
          <div className="mt-2">
            <div className="text-xs text-muted mb-1">How the score moved through the day (each cron run that changed it)</div>
            <Sparkline history={f.history} />
          </div>
        )}
      </section>

      <section aria-labelledby="fc-sched">
        <h4 id="fc-sched" className="hk-kicker mb-1">
          Schedule
        </h4>
        <Row k="scheduled (HKT)" v={hm(f.sched_ts)} />
        <Row k="estimated" v={hm(f.est_ts)} />
        <Row k="actual" v={hm(f.actual_ts)} />
        <Row k="terminal / gate" v={`${f.terminal ?? '—'} / ${f.gate ?? '—'}`} />
        {f.codeshares && <Row k="codeshares" v={<span className="text-xs break-words">{f.codeshares}</span>} />}
      </section>

      {aircraft && (
        <section aria-labelledby="fc-ac">
          <h4 id="fc-ac" className="hk-kicker mb-1">
            Aircraft (ADS-B)
          </h4>
          <Row k="callsign" v={aircraft.callsign || '—'} />
          <Row k="registration / type" v={`${aircraft.reg || '—'} / ${aircraft.type || '—'}`} />
          <Row k="altitude" v={aircraft.onGround ? 'on ground' : `${num(aircraft.altFt)} ft`} />
          <Row k="ground speed / track" v={`${aircraft.gsKt == null ? '—' : Math.round(aircraft.gsKt) + ' kt'} / ${aircraft.trackDeg == null ? '—' : Math.round(aircraft.trackDeg) + '°'}`} />
          <Row k="distance from HKIA" v={`${aircraft.distNm.toFixed(0)} nm`} />
        </section>
      )}
      <p className="text-[0.7rem] text-muted">
        P is a probability, not a verdict: 30 % means roughly 3 in 10 such flights leave more than 15 min late. Weather used for
        future flights = latest METAR (persistence), not a forecast.
      </p>
    </div>
  )
}
