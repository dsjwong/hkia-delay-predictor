import { ArrowDown, ArrowUp } from 'lucide-react'
import { Badge } from './ui/badge'
import { PBar } from './PBar'
import { Sparkline } from './Sparkline'
import { airlineName, destLabel } from '@/lib/data'
import type { Flight, Meta, WhyItem } from '@/lib/types'
import { dt, hm, num, pct, signed } from '@/lib/time'
import type { Aircraft } from '@/lib/adsb'
import { amberHex, SERIES_1, SERIES_2 } from '@/lib/theme'

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5 border-b border-border/60 last:border-0">
      <span className="text-xs text-muted">{k}</span>
      <span className="text-sm text-ink text-right hk-num">{v}</span>
    </div>
  )
}

/** One driver of the prediction: an arrow (up = pushed P up, amber; down = pushed it down, teal), the plain-English
 *  reason, and the size of the push in probability points. Direction is never carried by colour alone — the arrow
 *  glyph and the signed number both say it, and a visually-hidden word says it to a screen reader. */
export function WhyRow({ item }: { item: WhyItem }) {
  const [dir, text, pp] = item
  const up = dir > 0
  const Icon = up ? ArrowUp : ArrowDown
  return (
    <li className="flex items-baseline gap-2 py-1 border-b border-border/60 last:border-0">
      <Icon aria-hidden className="size-3.5 shrink-0 translate-y-0.5" style={{ color: up ? SERIES_1 : SERIES_2 }} />
      <span className="sr-only">{up ? 'raises the probability:' : 'lowers the probability:'}</span>
      <span className="text-sm text-ink flex-1">{text}</span>
      <span className="text-xs text-muted hk-num whitespace-nowrap" title="probability points">
        {signed(pp, 1)} pp
      </span>
    </li>
  )
}

/** "Why this prediction": the top three local SHAP attributions, or an empty state for an older snapshot. */
export function WhyBlock({ why }: { why?: WhyItem[] }) {
  if (!why?.length)
    return (
      <div className="text-sm text-muted bg-elev rounded-md px-3 py-2.5">
        No attribution in this snapshot — they are written for flights that have not departed yet.
      </div>
    )
  return (
    <>
      <ul>
        {why.map((w, i) => (
          <WhyRow key={i} item={w} />
        ))}
      </ul>
      <p className="text-[0.7rem] text-muted leading-relaxed mt-2">
        Attributions are local SHAP values for this single prediction, in probability points: they explain the model,
        not the world.
      </p>
    </>
  )
}

export function statusBadge(f: Flight) {
  if (f.status === 'cancelled')
    return (
      <Badge variant="crit" dot>
        cancelled
      </Badge>
    )
  if (f.status === 'departed')
    return (
      <Badge variant="ok" dot>
        departed {hm(f.actual_ts)}
      </Badge>
    )
  return <Badge>scheduled{f.est_ts ? ` · est ${hm(f.est_ts)}` : ''}</Badge>
}

/** Flight details: prediction, schedule vs actual, destination, prediction history sparkline, and (on the live map) the aircraft. */
export function FlightCard({
  flight: f,
  meta,
  aircraft,
}: {
  flight: Flight
  meta: Meta | null
  aircraft?: Aircraft | null
}) {
  const a = meta?.airports[f.dest]
  const hit = f.delay_min != null && f.p != null ? f.p >= 0.5 === f.delay_min > 15 : null
  return (
    <div className="space-y-5">
      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xl font-semibold tracking-tight">{f.flight_no}</span>
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
        <h4 id="fc-pred" className="hk-kicker mb-2">
          Prediction
        </h4>
        {f.p == null ? (
          <div className="text-sm text-muted bg-elev rounded-md px-3 py-2.5">
            Not scored yet — the cron scores not-yet-departed flights every 30 min.
          </div>
        ) : (
          <div className="hk-card bg-elev border-border/60 px-4 py-3">
            <div className="flex items-end justify-between gap-3">
              <div>
                <div className="text-xs text-muted">P(delay &gt; 15 min)</div>
                <div className="text-[2rem] leading-9 font-semibold tracking-tight" style={{ color: amberHex(f.p) }}>
                  {pct(f.p)}
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-muted">predicted delay</div>
                <div className="text-lg font-semibold hk-num">
                  {f.pred_min == null ? '—' : `${Math.round(f.pred_min)} min`}
                </div>
              </div>
            </div>
            <PBar p={f.p} width={999} className="w-full mt-2 [&>span:first-child]:flex-1 [&>span:last-child]:hidden" />
            <div className="mt-2 space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-muted">last scored</span>
                <span className="text-xs text-ink-2 hk-num">{dt(f.scored_at)}</span>
              </div>
              {f.delay_min != null && (
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-muted">actual delay</span>
                  <span className="text-sm hk-num inline-flex items-center gap-2">
                    {signed(f.delay_min)} min
                    {hit != null && (
                      <Badge variant={hit ? 'ok' : 'warn'} dot>
                        {hit ? 'hit' : 'miss'} at P ≥ 50 %
                      </Badge>
                    )}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
        {f.history && f.history.length > 1 && (
          <div className="mt-3">
            <div className="text-xs text-muted mb-1">Score through the day (each cron run that changed it)</div>
            <Sparkline history={f.history} />
          </div>
        )}
      </section>

      {/* only for flights that have not left: the exporter writes `why` for those, so gating on `p` alone would put an
          empty box on every departed-but-scored flight — two thirds of the day's table */}
      {f.p != null && f.status === 'scheduled' && (
        <section aria-labelledby="fc-why">
          <h4 id="fc-why" className="hk-kicker mb-2">
            Why this prediction
          </h4>
          <WhyBlock why={f.why} />
        </section>
      )}

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
          <Row
            k="ground speed / track"
            v={`${aircraft.gsKt == null ? '—' : Math.round(aircraft.gsKt) + ' kt'} / ${aircraft.trackDeg == null ? '—' : Math.round(aircraft.trackDeg) + '°'}`}
          />
          <Row k="distance from HKIA" v={`${aircraft.distNm.toFixed(0)} nm`} />
        </section>
      )}
      <p className="text-[0.7rem] text-muted leading-relaxed">
        P is a probability, not a verdict: 30 % means roughly 3 in 10 such flights leave more than 15 min late. Weather
        used for future flights = latest METAR (persistence), not a forecast.
      </p>
    </div>
  )
}
