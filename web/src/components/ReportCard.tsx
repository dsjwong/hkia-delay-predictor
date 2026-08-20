/** The live model report card — the hero of the Model route.
 *
 *  Everything here comes from model.json → live_eval, written by src/hkia/evaluate.compute: for every flight that has
 *  since departed, the LAST probability the service published before it left, scored against what actually happened.
 *  Nothing is smoothed and nothing weak is hidden: slices with too few flights are drawn with a "thin" label, and a
 *  slice with a single class shows "—" rather than a fabricated 0.5. */
import { Check, TrendingDown, TrendingUp, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Empty } from '@/components/ui/empty'
import { Tile } from '@/components/ui/tile'
import { PBar } from '@/components/PBar'
import { DailyAuc, LeadBucketBars } from '@/charts/ReportCharts'
import { Reliability } from '@/charts/ModelCharts'
import { num, signed } from '@/lib/time'
import type { LiveEval, NotableFlight } from '@/lib/types'

const f3 = (x: number | null | undefined) => (x == null ? '—' : x.toFixed(3))
const f1 = (x: number | null | undefined) => (x == null ? '—' : x.toFixed(1))

/** A metric delta as a pill: arrow + signed number + the 95 % bootstrap CI.
 *
 *  A delta whose CI straddles 0 is NOT coloured green — it gets a neutral pill and the words "within noise", because a
 *  +0.017 AUC over four days looks like a win and is not one. Colour is always a second cue behind the number. */
function Delta({
  value,
  ci,
  significant,
  digits = 3,
  lowerIsBetter = false,
  unit = '',
}: {
  value: number | null | undefined
  ci?: [number, number] | null
  significant?: boolean | null
  digits?: number
  lowerIsBetter?: boolean
  unit?: string
}) {
  if (value == null) return <span className="text-muted">baseline unavailable</span>
  const better = lowerIsBetter ? value < 0 : value > 0
  const Icon = value < 0 ? TrendingDown : TrendingUp
  const known = significant != null
  return (
    <span className="inline-flex items-center gap-1.5 flex-wrap">
      <Badge variant={!known ? (better ? 'ok' : 'crit') : significant ? 'ok' : 'default'} className="px-1.5">
        <Icon size={11} aria-hidden="true" />
        <span className="hk-num">
          {signed(value, digits)}
          {unit}
        </span>
      </Badge>
      {ci ? (
        <span className="text-muted hk-num" title="95 % confidence interval, paired bootstrap over the matured flights">
          95 % CI {signed(ci[0], digits)} … {signed(ci[1], digits)}
          {significant === false && <span className="text-muted"> · within noise</span>}
        </span>
      ) : (
        <span className="text-muted">vs baseline</span>
      )}
    </span>
  )
}

function ResultBadge({ f }: { f: NotableFlight }) {
  const late = f.delayed15 === 1
  const called = (f.p ?? 0) >= 0.5 === late
  return (
    <Badge variant={called ? 'ok' : 'crit'} className="px-1.5">
      {called ? <Check size={11} aria-hidden="true" /> : <X size={11} aria-hidden="true" />}
      {late ? `${num(f.delay_min)} min late` : 'on time'}
    </Badge>
  )
}

function NotableTable({ rows, caption }: { rows: NotableFlight[]; caption: string }) {
  if (!rows.length) return <Empty title="no flights in this slice yet" />
  return (
    <div className="rounded-lg border border-border overflow-auto">
      <table className="hk-table">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            <th>flight</th>
            <th>date</th>
            <th>to</th>
            <th className="text-right">P(delay &gt; 15)</th>
            <th className="text-right">pred</th>
            <th className="text-right">outcome</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((f, i) => (
            <tr key={`${f.date}-${f.flight_no}-${f.sched_ts ?? i}`}>
              <td className="hk-num whitespace-nowrap font-medium text-ink">{f.flight_no}</td>
              <td className="hk-num text-muted whitespace-nowrap">{f.date.slice(5)}</td>
              <td className="text-ink-2 whitespace-nowrap">{f.dest ?? '—'}</td>
              <td className="text-right">
                <PBar p={f.p} width={48} className="justify-end" />
              </td>
              <td className="hk-num text-right text-ink-2 whitespace-nowrap">{f1(f.pred_min)} min</td>
              <td className="text-right whitespace-nowrap">
                <ResultBadge f={f} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function ReportCard({ ev }: { ev: LiveEval }) {
  const m = ev.model ?? {}
  const b = ev.baseline_airline_hour && !ev.baseline_airline_hour.error ? ev.baseline_airline_hour : undefined
  const d = ev.deltas ?? undefined
  const ci = ev.bootstrap?.ci ?? {}
  const sig = ev.bootstrap?.beats_baseline ?? {}
  const cov = ev.coverage
  const hc = ev.notable?.high_confidence
  const span = ev.date_min && ev.date_max ? `${ev.date_min.slice(5)} → ${ev.date_max.slice(5)}` : `${ev.window_days} d`
  // Say plainly which margins this much data can actually establish, instead of letting four green pills imply all of them.
  const LABELS: Record<string, string> = { auc: 'AUC', brier: 'Brier', logloss: 'log loss', mae: 'MAE' }
  const won = (['auc', 'brier', 'logloss', 'mae'] as const).filter((k) => sig[k])
  const verdict = !ev.bootstrap
    ? 'on this much data the margins should be read as provisional.'
    : won.length
      ? `on this window the model is separably better on ${won.map((k) => LABELS[k]).join(', ')}; the rest are inside the noise.`
      : 'on this window none of the margins clear the noise yet.'

  // a failed export also arrives as status != 'ok'; showing "collecting" for it would hide a broken pipeline behind a
  // friendly message, so the two states are told apart
  const broken = ev.status?.startsWith('error')
  if (ev.status !== 'ok')
    return (
      <section className="space-y-3" aria-labelledby="report-card-h">
        <Header id="report-card-h" ev={ev} />
        <Card>
          <CardContent className="pt-4">
            {broken ? (
              <Empty
                tone="error"
                title="The live evaluation could not be computed for this snapshot."
                detail={ev.status}
              />
            ) : (
              <Empty
                title={
                  <>
                    Collecting — <b className="text-ink">{num(ev.n_matured)}</b> matured predictions so far (need ≥{' '}
                    {ev.min_n})
                  </>
                }
                detail="A prediction 'matures' when its flight departs; the score used is the last one published before departure. The report card appears once a week of scoring has accumulated."
              />
            )}
          </CardContent>
        </Card>
      </section>
    )

  return (
    <section className="space-y-4" aria-labelledby="report-card-h">
      <Header id="report-card-h" ev={ev} />

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        <Tile
          label="AUC (live)"
          value={f3(m.auc)}
          sub={<Delta value={d?.auc} ci={ci.auc} significant={sig.auc} />}
          tone="accent"
          hint={`Ranking quality on flights that have actually departed: the chance the model puts a random delayed flight above a random on-time one. The airline × hour lookup gets ${f3(b?.auc)}; a coin flip gets 0.500. The margin is shown with a 95 % paired-bootstrap interval — if it straddles 0, this window cannot tell the two apart.`}
        />
        <Tile
          label="Brier"
          value={f3(m.brier)}
          sub={<Delta value={d?.brier} ci={ci.brier} significant={sig.brier} lowerIsBetter />}
          hint="Mean squared error of the published probabilities — lower is better, and it punishes over-confidence as well as bad ranking."
        />
        <Tile
          label="MAE (min)"
          value={f1(m.mae)}
          sub={<Delta value={d?.mae} ci={ci.mae} significant={sig.mae} digits={1} lowerIsBetter unit=" min" />}
          hint="Typical error of the predicted delay in minutes on departed flights. Delays are heavy-tailed, so a few very late aircraft dominate this number."
        />
        <Tile
          label="Matured predictions"
          value={num(ev.n_matured)}
          sub={
            cov?.pct != null
              ? `${Math.round(cov.pct * 100)} % of the ${num(cov.n_departed)} departures ${span}`
              : `${ev.window_days}-day window · ${span}`
          }
          hint={`Departed flights that carry a score written before they left. The cron does not catch every flight: the ones it misses are usually the ones that left promptly, so the observed late rate here runs slightly above the airport's. Median lead time between the last score and the actual departure: ${num(ev.median_lead_min)} min.`}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>AUC per day — model vs baseline</CardTitle>
              <CardDescription>
                one point per HKT departure date; a day with no delayed flights has no AUC and leaves a gap
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            {ev.daily?.length ? (
              <DailyAuc rows={ev.daily} />
            ) : (
              <Empty title="no daily series in this snapshot" detail="Re-run python -m hkia.export_json." />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>AUC by forecast horizon</CardTitle>
              <CardDescription>
                minutes between the last score and the <i>scheduled</i> departure — deliberately not the actual one,
                which would slice by the outcome
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            {ev.lead_buckets?.length ? (
              <>
                <LeadBucketBars rows={ev.lead_buckets} thinAt={ev.min_slice_n} />
                <p className="text-[0.7rem] text-muted mt-2 leading-relaxed">
                  Measured against the timetable, because <code className="font-mono">actual − scored</code> is a
                  function of the delay itself: a flight is only ever "scored six hours before it left" because it left
                  six hours late, so bucketing on it would stratify by the outcome and make the worst-predicted flights
                  look like the best-predicted ones. <b className="text-ink-2">after STD</b> = the last score landed
                  after the scheduled time, i.e. the flight was already visibly running late.
                </p>
              </>
            ) : (
              <Empty title="no horizon buckets in this snapshot" detail="Re-run python -m hkia.export_json." />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Calibration on live data</CardTitle>
              <CardDescription>
                10 equal-width probability bins over the {num(ev.n_matured)} matured predictions; on the diagonal means
                "when it says 30 %, 30 % of them are late". Bins under {ev.cal_min_n ?? 30} flights are drawn hollow and
                left unconnected — an observed rate on six flights moves 17 points per flight.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            {ev.calibration?.length ? (
              <Reliability bins={ev.calibration} label="XGBoost (live)" minN={ev.cal_min_n} />
            ) : (
              <Empty title="no live calibration in this snapshot" detail="Re-run python -m hkia.export_json." />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>How this is computed</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-ink-2 leading-relaxed">
              Every 30 minutes a GitHub Actions cron scores every departure that has not left yet and appends the
              probability to the database. When the aircraft finally departs, that prediction "matures": the{' '}
              <b className="text-ink">last score written before the actual departure time</b> is locked in and compared
              with the real delay (actual − scheduled, {'>'} 15 min = late). The card above is the rolling{' '}
              <b className="text-ink">{ev.window_days}-day window</b> of those matured predictions —{' '}
              <span className="hk-num">{num(ev.n_matured)}</span> flights that departed {span}, of which{' '}
              <span className="hk-num">{Math.round((ev.delayed15_rate ?? 0) * 100)} %</span> were more than 15 minutes
              late. The comparison is the same baseline used at training time: the{' '}
              <b className="text-ink">airline × hour lookup table</b> — the historical delay rate for that airline in
              that hour of day, fitted on the training split only, with no weather and no congestion.
            </p>
            <p className="text-xs text-muted leading-relaxed">
              Nothing here is a back-test: these are the numbers the site actually showed, graded after the fact.{' '}
              {cov?.pct != null && (
                <>
                  Coverage is <span className="hk-num">{Math.round(cov.pct * 100)} %</span> —{' '}
                  <span className="hk-num">{num(cov.n_scored)}</span> of the{' '}
                  <span className="hk-num">{num(cov.n_departed)}</span> departures on those dates were scored in time;
                  the rest are excluded and are not a random sample, so the late rate above is the rate among scored
                  flights.{' '}
                </>
              )}
              Slices with fewer than {ev.min_slice_n ?? 100} flights are marked "thin" because their AUC is mostly
              noise, and every margin carries a 95 % bootstrap interval — {verdict}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Notable flights of the last {ev.window_days} days</CardTitle>
            <CardDescription>
              the calls the model got most right, and the ones it got most wrong — same window, same
              last-score-before-departure rule
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-2">
              <h4 className="hk-kicker">Confident and correct — high P, and they were late</h4>
              <NotableTable
                rows={ev.notable?.confident_correct ?? []}
                caption="Flights with the highest published probability that did depart more than 15 minutes late"
              />
              {hc != null && hc.n > 0 && (
                <p className="text-[0.7rem] text-muted leading-relaxed">
                  That table is picked <i>after</i> the fact, so it can only contain wins. The honest counterpart: of{' '}
                  <b className="text-ink-2">
                    all {num(hc.n)} calls published at P ≥ {Math.round(hc.threshold * 100)} %
                  </b>
                  , <span className="hk-num">{num(hc.n_late)}</span> were more than 15 minutes late (
                  {hc.rate == null ? '—' : `${Math.round(hc.rate * 100)} %`}).
                </p>
              )}
            </div>
            <div className="space-y-2">
              <h4 className="hk-kicker">Biggest misses — both directions</h4>
              <NotableTable
                rows={ev.notable?.worst_misses ?? []}
                caption="Flights with the largest gap between the published probability and what happened"
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}

function Header({ id, ev }: { id: string; ev: LiveEval }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
      <h3 id={id} className="text-base font-semibold tracking-tight text-ink">
        Model report card — live, graded after the fact
      </h3>
      <p className="text-xs text-muted">
        rolling {ev.window_days}-day window
        {ev.computed_at ? ` · computed ${ev.computed_at.slice(0, 16).replace('T', ' ')} UTC` : ''}
      </p>
    </div>
  )
}

/** The chip on the Live map header that links into the report card.
 *
 *  It only uses the word "beats" for a margin the bootstrap actually supports. With the current data that is MAE, not
 *  AUC — a landing-page claim of "beats the baseline" resting on a margin inside its own confidence interval is
 *  exactly the kind of thing this page exists to avoid. */
export function beatsBaselineText(ev: LiveEval | null | undefined): string | null {
  if (!ev || ev.status !== 'ok') return null
  const sig = ev.bootstrap?.beats_baseline
  const d = ev.deltas
  if (sig?.auc && d?.auc != null) return `beats baseline live: AUC ${signed(d.auc, 3)}`
  if (sig?.mae && d?.mae != null) return `live: MAE ${signed(d.mae, 1)} min vs baseline`
  if (ev.model?.auc != null) return `live report card: AUC ${ev.model.auc.toFixed(3)}`
  return null
}
