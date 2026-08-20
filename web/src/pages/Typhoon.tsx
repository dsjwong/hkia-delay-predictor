/** Case study — Typhoon Noul at HKIA, 24-26 Jul 2026.
 *
 *  A data story with a model retrospective, not "the model called it live": live scoring only began 2026-08-17, so no
 *  prediction was ever published for these flights. Everything the model says here is IN-SAMPLE (24-26 Jul sits in its
 *  validation split) and the page carries that flag in the UI — a banner, a badge on the retrospective card and a badge
 *  on the chart — not only in the prose. Data: web/public/data/case_noul.json, a static artefact written once by
 *  `python -m hkia.case_study`; the ingest cron never rewrites it.
 */
import { AlertTriangle, Info } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Empty } from '@/components/ui/empty'
import { Skeleton, SkeletonCard } from '@/components/ui/skeleton'
import { Tile } from '@/components/ui/tile'
import { CancelStrip, DelayWithSignalBands, GustPanel, PredVsObsBySignal } from '@/charts/CaseCharts'
import { useCaseStudy } from '@/lib/data'
import { dt, num, pct } from '@/lib/time'
import type { CaseStudy } from '@/lib/types'

const SIG = (s: number) => (s > 0 ? `T${s}` : 'none')

function PageSkeleton() {
  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Skeleton className="h-6 w-80" />
        <Skeleton className="h-3.5 w-[32rem]" />
      </div>
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <Tile key={i} label=" " value="" loading />
        ))}
      </div>
      <SkeletonCard body="h-72" />
      <div className="grid gap-4 lg:grid-cols-2">
        <SkeletonCard body="h-40" />
        <SkeletonCard body="h-40" />
      </div>
    </div>
  )
}

/** The honesty banner. Rendered before anything the model says, and repeated as a badge on each model block. */
function InSampleBanner({ c }: { c: CaseStudy }) {
  const r = c.retrospective
  return (
    <div className="hk-card border-warning/40 px-4 py-3 text-sm text-ink-2 leading-relaxed" role="note">
      <div className="flex items-center gap-2 mb-1">
        <AlertTriangle size={14} className="text-warning shrink-0" aria-hidden="true" />
        <span className="font-semibold text-ink">
          No prediction was published for these flights — this is a data story, not a live forecast.
        </span>
      </div>
      Live scoring began <b className="text-ink">{r?.live_scoring_began ?? '2026-08-17'}</b>, three weeks after Noul.
      The model numbers below were produced by re-running the shipped model over these flights after the fact, with the
      same feature builder
      {r && (
        <>
          {' '}
          — and 24–26 Jul falls inside its <b className="text-ink">validation split</b> ({r.val_dates[0]} →{' '}
          {r.val_dates[1]}), which was used for early stopping and model selection
        </>
      )}
      . They are <b className="text-ink">in-sample</b>: an illustration of what the model says about these hours, never
      a measurement of skill.
    </div>
  )
}

function Story({ c }: { c: CaseStudy }) {
  const h = c.headline
  const bySig = Object.fromEntries(c.by_signal.map((r) => [r.signal, r]))
  const b = c.baseline
  const r = c.retrospective
  const t8 = r?.by_signal.find((x) => x.signal === 8)
  const peakHour = h.peak_hour ? dt(h.peak_hour) : '—'
  const cpa = c.cancellations.by_airline[0]
  return (
    <div className="hk-card p-4 space-y-3 text-sm text-ink-2 leading-relaxed">
      <h3 className="text-sm font-semibold text-ink">What happened</h3>
      <p>
        Noul was the second tropical cyclone of the 2026 season to reach Hong Kong, and the only one in this dataset to
        go past a standby signal. The Observatory hoisted the No. 1 standby signal at{' '}
        <b className="text-ink">{dt(c.episode.first_signal)}</b> and walked it up through the sequence{' '}
        <b className="text-ink">{c.episode.sequence}</b> —{' '}
        {c.episode.signals.find((s) => s.signal === 9)
          ? `the hurricane-force No. 9 stood for ${num(c.episode.signals.find((s) => s.signal === 9)?.hours, 1)} hours through the small hours of 26 July`
          : 'peaking overnight'}{' '}
        — before the all-clear at <b className="text-ink">{dt(c.recovery.all_clear_ts)}</b>. Peak gust at the field was{' '}
        <b className="text-ink">{num(h.peak_gust_kt)} kt</b> and visibility fell to{' '}
        <b className="text-ink">{num(h.min_visib_sm, 1)} statute miles</b>.
      </p>
      <p>
        The airport did not fail gradually; it fell off a cliff at signal 8. With no signal in force the airport cancels{' '}
        <b className="text-ink">{pct(b.cancel_rate, 1)}</b> of departures and averages{' '}
        <b className="text-ink">{num(b.mean_delay, 1)} min</b> of delay. Under signal 3 the cancellation rate is already{' '}
        <b className="text-ink">{pct(bySig[3]?.cancel_rate, 0)}</b>; under signal 8 it is{' '}
        <b className="text-ink">{pct(bySig[8]?.cancel_rate, 0)}</b> and the flights that do leave average{' '}
        <b className="text-ink">{num(bySig[8]?.mean_delay, 0)} min</b> late. The worst hour of the episode,{' '}
        <b className="text-ink">{peakHour}</b>, averaged{' '}
        <b className="text-ink">{num(h.peak_hour_mean_delay, 0)} min</b> across {h.peak_hour_n} departures. Over the
        three signal days <b className="text-ink">{num(h.n_cancelled_episode)}</b> of {num(h.n_flights_episode)}{' '}
        scheduled departures were cancelled
        {cpa && (
          <>
            , {num(cpa.n_cancelled)} of them {cpa.name}&apos;s
          </>
        )}
        ; {h.n_hours_no_departures} clock hours in the window saw no departure at all.
      </p>
      <p>
        Recovery was slower than the storm. The signal came down at{' '}
        <b className="text-ink">{dt(c.recovery.all_clear_ts)}</b>, but hourly mean delay only returned to the no-signal
        baseline of {num(b.mean_delay, 1)} min at <b className="text-ink">{dt(c.recovery.recovered_at)}</b> —{' '}
        <b className="text-ink">{num(c.recovery.hours_to_recover, 0)} hours later</b>. The tail is worse than the mean:
        the ten longest delays all ran past the {c.clip.max}-minute clip this repo uses everywhere else, up to{' '}
        <b className="text-ink">{num(c.worst_flights[0]?.delay_min)} minutes</b> — aircraft and crews that ended up on
        the wrong side of the storm and left a day late.
      </p>
      {r && (
        <p>
          What would the model have said? Re-scored after the fact, it ranks these flights well — AUC{' '}
          <b className="text-ink">{num(r.overall.auc, 3)}</b> over {num(r.overall.n)} departures, flagging{' '}
          <b className="text-ink">{pct(r.overall.pct_flagged, 0)}</b> of them above P = {r.flag_threshold} against an
          observed late rate of {pct(r.overall.obs_rate, 0)} — but it badly under-calls the magnitude. Under signal 8 it
          expected <b className="text-ink">{num(t8?.mean_pred_delay, 0)} min</b> of delay where the airport actually ran{' '}
          <b className="text-ink">{num(t8?.mean_obs_delay, 0)} min</b> late. The signal features tell it &ldquo;worse
          than usual&rdquo;; nothing in the feature set tells it &ldquo;the airport has stopped&rdquo;, because the
          feature that would — how far behind the operation already is — is not in the model.
        </p>
      )}
      <p>
        The caveats matter more than the numbers. {r ? 'Every model figure on this page is in-sample: ' : ''}
        {r
          ? `these days sit inside the validation split (${r.val_dates[0]} → ${r.val_dates[1]}) that chose the model's stopping point, so a good AUC here is partly the model recognising days it has already seen. `
          : ''}
        One typhoon is one event: {num(bySig[8]?.n)} flights under signal 8 and {num(bySig[9]?.n)} under signal 9 is an
        anecdote, not a measured effect, and the extremes come from a handful of hours. Cancelled flights carry no delay
        label at all, so every average here is conditioned on the flight having eventually left — the 15 % of the
        schedule that vanished is counted separately, in the strip below, and never averaged in.
      </p>
    </div>
  )
}

export default function Typhoon() {
  const { data: c, error, loading } = useCaseStudy()
  if (error)
    return (
      <Empty
        tone="error"
        className="py-16"
        title="Could not load case_noul.json"
        detail={`${error}. The case study is a static artefact — regenerate it with \`python -m hkia.case_study\` and commit it.`}
      />
    )
  if (loading || !c) return <PageSkeleton />
  if (!c.hourly?.length)
    return <Empty className="py-16" title="The case study artefact is empty." detail={c.regenerate} />

  const h = c.headline
  const r = c.retrospective
  const predRows = (r?.by_signal ?? []).map((s) => ({
    signal: s.signal,
    pred_delay: s.mean_pred_delay,
    mean_delay: s.mean_obs_delay,
    n: s.n,
  }))
  return (
    <div className="space-y-5">
      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <h2 className="text-xl font-semibold tracking-tight">
            Case study — Typhoon {c.episode.name.charAt(0) + c.episode.name.slice(1).toLowerCase()} at HKIA
          </h2>
          <Badge variant="warn" dot>
            signal {c.episode.sequence}
          </Badge>
        </div>
        <p className="text-xs text-muted mt-1">
          {c.window.days[0]} → {c.window.days[c.window.days.length - 1]} HKT, hour by hour, from the flight table, the
          VHHH METAR archive and HKO&apos;s tropical-cyclone warning database. Static snapshot — generated once by{' '}
          <code className="font-mono">{c.regenerate}</code>, not refreshed by the cron.
        </p>
      </div>

      <InSampleBanner c={c} />

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        <Tile
          label="Peak signal"
          value={`No. ${h.peak_signal}`}
          sub={c.episode.sequence}
          tone="warn"
          hint="Highest tropical-cyclone warning signal hoisted during the episode (HKO scale 1 · 3 · 8 · 9 · 10)."
        />
        <Tile
          label="Departures cancelled"
          value={num(h.n_cancelled_episode)}
          sub={`${pct(h.cancel_rate_episode, 1)} of ${num(h.n_flights_episode)} on the 3 signal days`}
          tone="crit"
        />
        <Tile
          label="Peak hourly mean delay"
          value={`${num(h.peak_hour_mean_delay)} min`}
          sub={`${dt(h.peak_hour)} · ${h.peak_hour_n} flights`}
          tone="accent"
          hint={`Busiest-hour mean over departures that eventually left; delays outside [${c.clip.min}, ${c.clip.max}] min are excluded, as everywhere else in this app.`}
        />
        <Tile
          label="Hours to recover"
          value={h.hours_to_recover == null ? '—' : `${num(h.hours_to_recover)} h`}
          sub={`after the all-clear, back to ${num(c.baseline.mean_delay, 1)} min`}
          hint={c.recovery.rule}
        />
      </div>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Mean departure delay by hour, with the signal in force behind it</CardTitle>
            <CardDescription>
              minutes, scheduled hour HKT · one y-axis: the signal is a labelled band, not a second scale · hover any
              hour for counts and weather
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <DelayWithSignalBands hours={c.hourly} />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Wind at the field</CardTitle>
              <CardDescription>VHHH hourly METAR, knots — own panel, own axis</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <GustPanel hours={c.hourly} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Cancellations per hour</CardTitle>
              <CardDescription>
                {num(c.cancellations.total)} in the window — these flights have no delay label and are in no average
                above
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <CancelStrip hours={c.hourly} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Story c={c} />
        </div>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Signal sequence</CardTitle>
              <CardDescription>HKO tropical-cyclone warning database, HKT</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="px-0 pb-0">
            <div className="rounded-b-xl border-t border-border overflow-auto">
              <table className="hk-table">
                <thead>
                  <tr>
                    <th>Signal</th>
                    <th>from</th>
                    <th>to</th>
                    <th className="text-right">hours</th>
                  </tr>
                </thead>
                <tbody>
                  {c.episode.signals.map((s) => (
                    <tr key={s.start}>
                      <td className="font-medium whitespace-nowrap">
                        No. {s.signal}
                        {s.direction && <span className="text-muted"> {s.direction}</span>}
                      </td>
                      <td className="hk-num whitespace-nowrap">{dt(s.start).replace(' HKT', '')}</td>
                      <td className="hk-num whitespace-nowrap">{dt(s.end).replace(' HKT', '')}</td>
                      <td className="hk-num text-right">{num(s.hours, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 items-start">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Totals by signal level</CardTitle>
                <CardDescription>
                  signal in force at the scheduled time, inside the case-study window; the baseline row is every
                  departure in the database with no signal in force
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="px-0 pb-0">
              <div className="rounded-b-xl border-t border-border overflow-auto">
                <table className="hk-table">
                  <thead>
                    <tr>
                      <th>Signal</th>
                      <th className="text-right">flights</th>
                      <th className="text-right">cancelled</th>
                      <th className="text-right">mean delay</th>
                      <th className="text-right">&gt; 15 min</th>
                    </tr>
                  </thead>
                  <tbody>
                    {c.by_signal.map((s) => (
                      <tr key={s.signal}>
                        <td className="font-medium">{SIG(s.signal)}</td>
                        <td className="hk-num text-right">{num(s.n)}</td>
                        <td className="hk-num text-right">
                          {num(s.n_cancelled)} <span className="text-muted">({pct(s.cancel_rate, 0)})</span>
                        </td>
                        <td className="hk-num text-right">{num(s.mean_delay, 1)}</td>
                        <td className="hk-num text-right">{pct(s.pct15, 0)}</td>
                      </tr>
                    ))}
                    <tr className="text-muted">
                      <td className="font-medium">baseline</td>
                      <td className="hk-num text-right">{num(c.baseline.n)}</td>
                      <td className="hk-num text-right">
                        {num(c.baseline.n_cancelled)} <span>({pct(c.baseline.cancel_rate, 1)})</span>
                      </td>
                      <td className="hk-num text-right">{num(c.baseline.mean_delay, 1)}</td>
                      <td className="hk-num text-right">{pct(c.baseline.pct15, 0)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>Who lost flights</CardTitle>
                <CardDescription>
                  cancellations in the window by operating airline, and the destinations that lost the most
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                {c.cancellations.by_airline.map((a) => {
                  const w = c.cancellations.by_airline[0].n_cancelled || 1
                  return (
                    <div key={a.airline} className="flex items-center gap-3 text-xs">
                      <span className="w-40 shrink-0 truncate text-ink-2">
                        {a.name} <span className="text-muted">({a.airline})</span>
                      </span>
                      <span className="flex-1 h-2 rounded-sm bg-elev overflow-hidden" aria-hidden="true">
                        <span
                          className="block h-full rounded-sm bg-critical"
                          style={{ width: `${Math.max(2, (a.n_cancelled / w) * 100)}%` }}
                        />
                      </span>
                      <span className="hk-num w-28 text-right text-ink-2">
                        {num(a.n_cancelled)} of {num(a.n_sched)} <span className="text-muted">({pct(a.rate, 0)})</span>
                      </span>
                    </div>
                  )
                })}
              </div>
              <div className="text-xs text-muted leading-relaxed">
                Worst-hit destinations:{' '}
                {c.cancellations.by_dest.map((d, i) => (
                  <span key={d.dest}>
                    {i > 0 && ' · '}
                    <span className="text-ink-2">{d.city}</span> ({d.dest}) {d.n_cancelled}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>The ten longest delays</CardTitle>
              <CardDescription>
                actual departure minus scheduled, uncapped — every one of these is past the {c.clip.max}-minute clip and
                excluded from the averages
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="px-0 pb-0">
            <div className="rounded-b-xl border-t border-border overflow-auto">
              <table className="hk-table">
                <thead>
                  <tr>
                    <th>Flight</th>
                    <th>To</th>
                    <th className="text-right">scheduled</th>
                    <th className="text-right">delay</th>
                    <th className="text-right">signal</th>
                  </tr>
                </thead>
                <tbody>
                  {c.worst_flights.map((f) => (
                    <tr key={f.flight_no + f.sched_ts}>
                      <td>
                        <span className="hk-num">{f.flight_no}</span>{' '}
                        <span className="text-muted">{f.airline_name}</span>
                      </td>
                      <td>
                        {f.dest_city} <span className="text-muted">({f.dest})</span>
                      </td>
                      <td className="hk-num text-right whitespace-nowrap">{dt(f.sched_ts).replace(' HKT', '')}</td>
                      <td className="hk-num text-right text-accent whitespace-nowrap">
                        {num(f.delay_min)}
                        <span className="text-muted"> min</span>
                      </td>
                      <td className="hk-num text-right">{SIG(f.signal)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      {r && (
        <Card className="border-warning/40">
          <CardHeader>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <CardTitle>Model retrospective</CardTitle>
                <Badge variant="warn" dot>
                  in-sample — illustration only
                </Badge>
              </div>
              <CardDescription>
                model <span className="font-mono">{r.model_version}</span> re-run over the episode with the training
                feature builder. These days are inside its validation split ({r.val_dates[0]} → {r.val_dates[1]}); no
                score was ever published live. Not a skill measurement.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <PredVsObsBySignal rows={predRows} />
            <div className="rounded-lg border border-border overflow-auto">
              <table className="hk-table">
                <thead>
                  <tr>
                    <th>Signal</th>
                    <th className="text-right">n</th>
                    <th className="text-right">observed &gt; 15 min</th>
                    <th className="text-right">flagged P &gt; {r.flag_threshold}</th>
                    <th className="text-right">AUC</th>
                    <th className="text-right">predicted delay</th>
                    <th className="text-right">observed delay</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="font-medium">
                    <td>all</td>
                    <td className="hk-num text-right">{num(r.overall.n)}</td>
                    <td className="hk-num text-right">{pct(r.overall.obs_rate, 0)}</td>
                    <td className="hk-num text-right">{pct(r.overall.pct_flagged, 0)}</td>
                    <td className="hk-num text-right">{num(r.overall.auc, 3)}</td>
                    <td className="hk-num text-right">{num(r.overall.mean_pred_delay)}</td>
                    <td className="hk-num text-right">{num(r.overall.mean_obs_delay)}</td>
                  </tr>
                  {r.by_signal.map((s) => (
                    <tr key={s.signal}>
                      <td>{SIG(s.signal)}</td>
                      <td className="hk-num text-right">{num(s.n)}</td>
                      <td className="hk-num text-right">{pct(s.obs_rate, 0)}</td>
                      <td className="hk-num text-right">{pct(s.pct_flagged, 0)}</td>
                      <td className="hk-num text-right">
                        {s.n < 30 ? <span className="text-muted">thin, n={s.n}</span> : num(s.auc, 3)}
                      </td>
                      <td className="hk-num text-right">{num(s.mean_pred_delay)}</td>
                      <td className="hk-num text-right">{num(s.mean_obs_delay)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted leading-relaxed max-w-[80ch]">{r.note}</p>
          </CardContent>
        </Card>
      )}

      {(c.other_episodes.length > 0 || c.other_monsoon) && (
        <div className="hk-card px-4 py-3 text-sm text-ink-2 leading-relaxed flex gap-2">
          <Info size={14} className="text-muted shrink-0 mt-1" aria-hidden="true" />
          <div>
            <span className="font-semibold text-ink">Noul was not the only weather in the window.</span> The data also
            covers{' '}
            {c.other_episodes.map((e, i) => (
              <span key={e.tc_id + e.start}>
                {i > 0 && ', '}
                Typhoon {e.name} (peak No. {e.peak_signal}, {e.start.slice(0, 10)} → {e.end.slice(0, 10)})
              </span>
            ))}
            {c.other_monsoon && (
              <>
                {c.other_episodes.length > 0 ? ' and ' : ''}
                {c.other_monsoon.n} strong-monsoon episodes ({c.other_monsoon.date_min} → {c.other_monsoon.date_max})
              </>
            )}
            . None went past a No. 1 standby signal, so none of them shut the airport — Noul is the only episode in this
            dataset with a signal 8 or above.
          </div>
        </div>
      )}

      <p className="text-xs text-muted leading-relaxed">
        {c.clip.note}. Sources: {Object.values(c.sources).join(' · ')}. Generated {dt(c.generated_at)}.
      </p>
    </div>
  )
}
