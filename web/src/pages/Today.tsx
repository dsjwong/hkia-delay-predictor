import { useMemo, useState } from 'react'
import { Tile } from '@/components/ui/tile'
import { Segmented } from '@/components/ui/segmented'
import { Sheet } from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { SkeletonCard, SkeletonRows } from '@/components/ui/skeleton'
import { Empty } from '@/components/ui/empty'
import { PBar } from '@/components/PBar'
import { FlightCard, statusBadge } from '@/components/FlightCard'
import { WeatherStrip } from '@/components/WeatherStrip'
import { HourlyBars, Timeline, type HourRow } from '@/charts/TodayCharts'
import { airlineName, useDepartures } from '@/lib/data'
import { useMetaCtx } from '@/lib/meta-context'
import type { Flight } from '@/lib/types'
import { dateLong, hm, hourHKT, num, pct, signed } from '@/lib/time'

type Which = 'yesterday' | 'today' | 'tomorrow'

export default function Today() {
  const { meta, weather } = useMetaCtx()
  const [which, setWhich] = useState<Which>('today')
  const deps = useDepartures(which)
  const [sel, setSel] = useState<Flight | null>(null)
  const [airline, setAirline] = useState<string>('')
  const [hours, setHours] = useState<[number, number]>([0, 23])
  const [onlyFuture, setOnlyFuture] = useState(false)
  const [hideCancelled, setHideCancelled] = useState(true)
  const [q, setQ] = useState('')

  const loading = deps.loading && !deps.data
  const flights = useMemo(() => deps.data?.flights ?? [], [deps.data])
  const names = (c: string | null) => airlineName(meta.data, c)
  const scored = flights.filter((f) => f.p != null)
  const nDep = flights.filter((f) => f.status === 'departed').length
  const nCan = flights.filter((f) => f.status === 'cancelled').length
  const meanP = scored.length ? scored.reduce((s, f) => s + (f.p as number), 0) / scored.length : null
  const nHi = scored.filter((f) => (f.p as number) >= 0.5).length
  const obs = flights.filter((f) => f.delay_min != null).map((f) => f.delay_min as number)
  const obsLate = obs.length ? obs.filter((d) => d > 15).length / obs.length : null
  const obsMean = obs.length ? obs.reduce((a, b) => a + b, 0) / obs.length : null

  const byHour: HourRow[] = useMemo(() => {
    const rows: HourRow[] = Array.from({ length: 24 }, (_, h) => ({ hour: h, n: 0, p: null, n_dep: 0, obs: null }))
    const acc = rows.map(() => ({ pSum: 0, pN: 0, late: 0, dep: 0, n: 0 }))
    for (const f of flights) {
      if (f.status === 'cancelled') continue
      const h = hourHKT(f.sched_ts)
      if (h < 0) continue
      acc[h].n++
      if (f.p != null) {
        acc[h].pSum += f.p
        acc[h].pN++
      }
      if (f.delay_min != null) {
        acc[h].dep++
        if (f.delay_min > 15) acc[h].late++
      }
    }
    return rows.map((r, h) => ({
      ...r,
      n: acc[h].n,
      p: acc[h].pN ? acc[h].pSum / acc[h].pN : null,
      n_dep: acc[h].dep,
      obs: acc[h].dep ? acc[h].late / acc[h].dep : null,
    }))
  }, [flights])

  const airlines = useMemo(() => {
    const m = new Map<string, number>()
    for (const f of flights) if (f.airline) m.set(f.airline, (m.get(f.airline) ?? 0) + 1)
    return [...m.entries()].sort((a, b) => b[1] - a[1])
  }, [flights])

  const view = flights.filter((f) => {
    if (airline && f.airline !== airline) return false
    const h = hourHKT(f.sched_ts)
    if (h < hours[0] || h > hours[1]) return false
    if (onlyFuture && f.status !== 'scheduled') return false
    if (hideCancelled && f.status === 'cancelled') return false
    if (
      q &&
      !`${f.flight_no} ${f.dest} ${names(f.airline)} ${f.codeshares ?? ''}`.toLowerCase().includes(q.toLowerCase())
    )
      return false
    return true
  })
  const hits = view.filter((f) => f.delay_min != null && f.p != null)
  const hitRate = hits.length
    ? hits.filter((f) => (f.p as number) >= 0.5 === (f.delay_min as number) > 15).length / hits.length
    : null
  const m = weather.data?.metar
  const pad2 = (n: number) => String(n).padStart(2, '0')

  return (
    <div className="space-y-5">
      {/* page header */}
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">
            Departures
            <span className="text-ink-2 font-normal"> — {dateLong(deps.data?.date ?? meta.data?.dates[which])}</span>
          </h2>
          <p className="text-xs text-muted mt-1">
            P(delay &gt; 15) and predicted minutes are the latest cron score of each not-yet-departed flight; departed
            flights keep their last score so hits and misses stay visible.
          </p>
        </div>
        <Segmented<Which>
          value={which}
          onChange={setWhich}
          label="Day (HKT)"
          options={[
            { value: 'yesterday', label: 'Yesterday' },
            { value: 'today', label: 'Today' },
            { value: 'tomorrow', label: 'Tomorrow' },
          ]}
        />
      </div>

      {deps.error && (
        <Card>
          <Empty tone="error" title="Could not load the snapshot" detail={deps.error} />
        </Card>
      )}

      {/* KPI tiles */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
        <Tile
          label="Flights"
          value={num(flights.length)}
          sub={`${nDep} departed · ${nCan} cancelled`}
          loading={loading}
        />
        <Tile
          label="Predicted > 15 min late"
          value={pct(meanP)}
          tone="accent"
          loading={loading}
          sub={scored.length ? `mean P · ${nHi} flights with P ≥ 50 %` : 'nothing scored yet'}
          hint="Mean of the latest P(delay > 15) over scored flights — the share of today's departures the model expects to leave more than 15 min late."
        />
        <Tile
          label="Observed so far"
          value={pct(obsLate)}
          loading={loading}
          sub={obs.length ? `> 15 min late · mean ${num(obsMean)} min` : 'no departures yet'}
        />
        <Tile
          label="METAR VHHH"
          value={m?.flt_cat ?? '—'}
          loading={weather.loading && !weather.data}
          sub={
            m
              ? `${m.wdir ?? 'VRB'}°/${m.wspd_kt ?? '—'} kt${m.wgst_kt ? ' G' + m.wgst_kt : ''} · vis ${m.visib ?? '—'} sm · ${m.temp_c ?? '—'}°C`
              : 'no METAR'
          }
          hint={m ? `${m.raw_ob} (${hm(m.report_time)} HKT)` : undefined}
        />
        <Tile
          label="HKO"
          loading={weather.loading && !weather.data}
          value={
            weather.data?.tc_active.length
              ? `TC ${weather.data.tc_active[0].signal}`
              : weather.data?.hko_warnings.length
                ? String(weather.data.hko_warnings.length)
                : 'none'
          }
          sub={
            weather.data?.tc_active.length
              ? (weather.data.tc_active[0].tc_name ?? 'signal in force')
              : weather.data?.hko_warnings.map((w) => w.name).join(', ') || 'nothing in force'
          }
          tone={weather.data?.tc_active.length ? 'crit' : weather.data?.hko_warnings.length ? 'warn' : undefined}
        />
      </div>
      <WeatherStrip compact />

      {/* charts */}
      <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
        {loading ? (
          <>
            <SkeletonCard body="h-64" />
            <SkeletonCard body="h-64" />
          </>
        ) : (
          <>
            <Card>
              <CardHeader>
                <div>
                  <CardTitle>Flights through the day</CardTitle>
                  <CardDescription>
                    P(delay &gt; 15 min) by scheduled time (HKT); click a dot for the flight card
                  </CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                {scored.length ? (
                  <Timeline flights={flights} names={names} onPick={setSel} />
                ) : (
                  <Empty title="Nothing scored yet" detail="The cron scores not-yet-departed flights every 30 min." />
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <div>
                  <CardTitle>By scheduled hour</CardTitle>
                  <CardDescription>predicted vs observed late share</CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                {scored.length ? (
                  <HourlyBars rows={byHour} />
                ) : (
                  <Empty title="Nothing scored yet" detail="Hourly bars appear once the first scores land." />
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* flights table */}
      <Card aria-labelledby="tbl-h">
        <CardHeader className="flex-col items-stretch gap-3">
          <div className="flex items-baseline justify-between gap-3">
            <CardTitle id="tbl-h">Flights</CardTitle>
            <span className="text-xs text-muted hk-num">{loading ? '' : `${view.length} of ${flights.length}`}</span>
          </div>
          <div className="flex flex-wrap items-end gap-3 text-xs">
            <label className="flex flex-col gap-1">
              <span className="text-muted">Airline</span>
              <select className="hk-input" value={airline} onChange={(e) => setAirline(e.target.value)}>
                <option value="">all airlines</option>
                {airlines.map(([c, n]) => (
                  <option key={c} value={c}>
                    {names(c)} ({c}, {n})
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-muted hk-num">
                Scheduled hour {pad2(hours[0])}–{pad2(hours[1])} (HKT)
              </span>
              <span className="flex items-center gap-2 h-8">
                <input
                  type="range"
                  min={0}
                  max={23}
                  value={hours[0]}
                  aria-label="from hour"
                  className="accent-[#f59e0b]"
                  onChange={(e) => setHours([Math.min(+e.target.value, hours[1]), hours[1]])}
                />
                <input
                  type="range"
                  min={0}
                  max={23}
                  value={hours[1]}
                  aria-label="to hour"
                  className="accent-[#f59e0b]"
                  onChange={(e) => setHours([hours[0], Math.max(+e.target.value, hours[0])])}
                />
              </span>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-muted">Search</span>
              <input
                className="hk-input w-44"
                placeholder="flight, airline, dest"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </label>
            <label className="inline-flex items-center gap-1.5 h-8 text-ink-2 cursor-pointer">
              <input
                type="checkbox"
                className="accent-[#f59e0b]"
                checked={onlyFuture}
                onChange={(e) => setOnlyFuture(e.target.checked)}
              />{' '}
              not yet departed only
            </label>
            <label className="inline-flex items-center gap-1.5 h-8 text-ink-2 cursor-pointer">
              <input
                type="checkbox"
                className="accent-[#f59e0b]"
                checked={hideCancelled}
                onChange={(e) => setHideCancelled(e.target.checked)}
              />{' '}
              hide cancelled
            </label>
          </div>
        </CardHeader>
        {loading ? (
          <SkeletonRows rows={8} cols={6} />
        ) : view.length === 0 ? (
          <Empty
            title="No flights match these filters"
            detail={
              flights.length ? 'Widen the hour range or clear the search.' : 'The snapshot has no flights for this day.'
            }
          />
        ) : (
          <div className="max-h-[640px] overflow-auto border-t border-border">
            <table className="hk-table min-w-[900px]">
              <thead>
                <tr>
                  {[
                    'Sched',
                    'Flight',
                    'Airline',
                    'To',
                    'Status',
                    'Actual',
                    'P(delay > 15)',
                    'Pred min',
                    'Actual delay',
                    'Hit?',
                    'Gate',
                    'Codeshares',
                  ].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {view.map((f) => {
                  const hit = f.delay_min != null && f.p != null ? f.p >= 0.5 === f.delay_min > 15 : null
                  return (
                    <tr
                      key={f.flight_no + f.sched_ts}
                      tabIndex={0}
                      role="button"
                      onClick={() => setSel(f)}
                      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), setSel(f))}
                      className="hk-row"
                      title="open the flight card"
                    >
                      <td className="hk-num text-ink-2">{hm(f.sched_ts)}</td>
                      <td className="font-medium whitespace-nowrap">{f.flight_no}</td>
                      <td className="text-ink-2 whitespace-nowrap">{names(f.airline)}</td>
                      <td className="text-ink-2" title={meta.data?.airports[f.dest]?.city}>
                        {f.dest}
                      </td>
                      <td>{statusBadge(f)}</td>
                      <td className="hk-num text-ink-2">{hm(f.actual_ts)}</td>
                      <td>
                        <PBar p={f.p} />
                      </td>
                      <td className="hk-num">{f.pred_min == null ? '—' : Math.round(f.pred_min)}</td>
                      <td className="hk-num">{f.delay_min == null ? '—' : signed(f.delay_min)}</td>
                      <td>
                        {hit == null ? (
                          ''
                        ) : (
                          <Badge variant={hit ? 'ok' : 'warn'} dot>
                            {hit ? 'hit' : 'miss'}
                          </Badge>
                        )}
                      </td>
                      <td className="text-ink-2">{f.gate ?? ''}</td>
                      <td className="text-[0.7rem] text-muted max-w-[260px] truncate" title={f.codeshares ?? ''}>
                        {f.codeshares ?? ''}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        <CardContent className="pt-3 space-y-1.5 border-t border-border">
          {hits.length > 0 && hitRate != null && (
            <p className="text-xs text-muted">
              Among the {hits.length} departed flights with a score, 'P ≥ 50 % ⇔ delayed &gt; 15 min' was right{' '}
              {pct(hitRate)} of the time (observed delayed rate{' '}
              {pct(hits.filter((f) => (f.delay_min as number) > 15).length / hits.length)}). A 50 % cut is just for
              eyeballing — the model outputs probabilities, see Model.
            </p>
          )}
          <p className="text-xs text-muted">
            P(delay &gt; 15) is a probability, not a verdict: 30 % means roughly 3 in 10 such flights leave more than 15
            min late. Weather used for future flights = latest METAR (persistence), not a forecast.
          </p>
        </CardContent>
      </Card>

      <Sheet open={!!sel} onClose={() => setSel(null)} title={sel ? `${sel.flight_no} · ${names(sel.airline)}` : ''}>
        {sel && <FlightCard flight={sel} meta={meta.data} />}
      </Sheet>
    </div>
  )
}
