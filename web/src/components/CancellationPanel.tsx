/** Cancellations across the whole data window — descriptive, deliberately not a model.
 *  Data: cancellations.json (hkia.export_json.cancellations). The db holds ~660 cancelled departures, more than half on a
 *  handful of disruption days, so there is nothing to train a classifier on that would not just be "is a typhoon up".
 *  Renders nothing if the snapshot is missing or malformed: it is a supplement to the Noul case study, never a blocker. */
import { Info } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tile } from '@/components/ui/tile'
import { CancelByHour } from '@/charts/CancelCharts'
import { HBar } from '@/charts/HBar'
import { CRITICAL } from '@/charts/tokens'
import { useCancellations } from '@/lib/data'
import { num, pct } from '@/lib/time'
import type { Cancellations } from '@/lib/types'

const ci = (c: [number, number] | null) => (c ? `${pct(c[0], 2)} – ${pct(c[1], 2)}` : '—')

export function CancellationBody({ c }: { c: Cancellations }) {
  const s = c.summary
  if (!s) return null
  const sig = c.by_signal ?? []
  const hi = sig.filter((r) => r.signal >= 3)
  const days = c.days ?? []
  return (
    <section className="space-y-4" aria-labelledby="cancel-h">
      <div>
        <h2 id="cancel-h" className="text-lg font-semibold tracking-tight">
          Cancellations across the whole window
        </h2>
        <p className="text-xs text-muted mt-1">
          {s.date_min} → {s.date_max} ({num(s.n_days)} complete HKT days). Descriptive counts, not a forecast: the data
          has too few, too clustered cancellations to train anything on, so the app does not predict them.
        </p>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        <Tile
          label="Departures cancelled"
          value={num(s.n_cancelled)}
          sub={`${pct(s.rate, 2)} of ${num(s.n_flights)} scheduled`}
          tone="crit"
        />
        <Tile
          label="Ordinary-day rate"
          value={pct(s.ordinary.rate, 2)}
          sub={`${num(s.ordinary.n_cancelled)} of ${num(s.ordinary.n)} · 95 % CI ${ci(s.ordinary.ci)}`}
          hint={`Excludes signal No. 3 and above and any day on which ≥ ${pct(s.disruption_rate, 0)} of the schedule was cancelled. That rule is chosen after seeing the outcome, so read it as a description of the quiet days, not an out-of-sample rate.`}
        />
        <Tile
          label="On storm / disruption days"
          value={pct(s.share_on_disruption_or_signal3, 0)}
          sub={`of all cancellations · ${s.disruption_days.length} days`}
          hint="Share of cancelled departures that fall on a disruption day or under signal No. 3 or higher."
        />
        <Tile
          label="Top 3 days"
          value={pct(s.top3_days_share, 0)}
          sub={`of all cancellations · ${num(s.n_days_with_cancellations)} of ${num(s.n_days)} days had any`}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Cancellation rate by HKO signal in force</CardTitle>
              <CardDescription>
                Signal at the scheduled departure time. The No. 3 and above rows come from very few storms (see the days
                column) — read them as anecdotes, not a measured dose-response.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <HBar
              rows={sig.map((r) => ({
                label: r.signal === 0 ? 'no signal' : `signal ${r.label}`,
                value: r.rate ?? 0,
                n: r.n,
                extra: [
                  ['cancelled', `${num(r.n_cancelled)} of ${num(r.n)}`],
                  ['95 % CI', ci(r.ci)],
                ],
              }))}
              fmt={(v) => pct(v, v < 0.1 ? 1 : 0)}
              xDomain={[0, 1]}
              color={CRITICAL}
            />
            <div className="rounded-lg border border-border overflow-auto">
              <table className="hk-table">
                <thead>
                  <tr>
                    <th>Signal</th>
                    <th className="text-right">departures</th>
                    <th className="text-right">cancelled</th>
                    <th className="text-right">rate</th>
                    <th className="text-right">95 % CI</th>
                    <th className="text-right">days</th>
                  </tr>
                </thead>
                <tbody>
                  {sig.map((r) => (
                    <tr key={r.signal}>
                      <td>{r.signal === 0 ? 'none' : r.label}</td>
                      <td className="hk-num text-right">{num(r.n)}</td>
                      <td className="hk-num text-right">{num(r.n_cancelled)}</td>
                      <td className="hk-num text-right">{pct(r.rate, 2)}</td>
                      <td className="hk-num text-right text-muted">{ci(r.ci)}</td>
                      <td className="hk-num text-right">{num(r.n_days)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {hi.length > 0 && (
              <p className="text-xs text-muted leading-relaxed">
                Signal No. 1 is a standby signal: its rate is above the quiet-day rate but still about {pct(sig.find((r) => r.signal === 1)?.rate, 1)}.
                The real step is at No. 3 and above.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>The days that hold the cancellations</CardTitle>
              <CardDescription>
                Top days by number cancelled. A day with signal &ldquo;none&rdquo; near the top is a cancellation spike
                this dataset cannot attribute to a typhoon.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border border-border overflow-auto">
              <table className="hk-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th className="text-right">cancelled</th>
                    <th className="text-right">of</th>
                    <th className="text-right">rate</th>
                    <th>signal</th>
                    <th>most affected</th>
                  </tr>
                </thead>
                <tbody>
                  {days.map((d) => (
                    <tr key={d.date}>
                      <td className="hk-num">{d.date}</td>
                      <td className="hk-num text-right">{num(d.n_cancelled)}</td>
                      <td className="hk-num text-right text-muted">{num(d.n)}</td>
                      <td className="hk-num text-right">{pct(d.rate, 1)}</td>
                      <td>{d.signal > 0 ? `No. ${d.signal}` : 'none'}</td>
                      <td className="text-ink-2">
                        {d.top_airline ?? '—'}
                        {d.top_airline_share != null && <span className="text-muted"> ({pct(d.top_airline_share, 0)})</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>By scheduled hour, ordinary days</CardTitle>
              <CardDescription>
                Hours with fewer than 100 departures are left out. Quiet-day cancellations are a fraction of a percent
                at every hour; no hour is a reliable danger zone.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>{c.by_hour && <CancelByHour rows={c.by_hour} />}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>By airline, ordinary days</CardTitle>
              <CardDescription>
                Airlines with at least {num(c.min_cell_airline ?? 500)} ordinary-day departures; n is shown at each bar.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <HBar
              rows={(c.by_airline ?? []).map((r) => ({
                label: r.name,
                value: r.rate ?? 0,
                n: r.n,
                extra: [
                  ['cancelled', `${num(r.n_cancelled)} of ${num(r.n)}`],
                  ['95 % CI', ci(r.ci)],
                ],
              }))}
              fmt={(v) => pct(v, 1)}
              color={CRITICAL}
            />
          </CardContent>
        </Card>
      </div>

      <div className="hk-card px-4 py-3 text-sm text-ink-2 leading-relaxed flex gap-2">
        <Info size={14} className="text-muted shrink-0 mt-1" aria-hidden="true" />
        <div>
          <span className="font-semibold text-ink">Why there is no cancellation model.</span> {num(s.n_cancelled)}{' '}
          cancellations in {num(s.n_days)} days, {pct(s.top3_days_share, 0)} of them on three days and{' '}
          {pct(s.share_on_disruption_or_signal3, 0)} on storm or disruption days. A classifier
          trained on that would learn &ldquo;is a signal up&rdquo; (which is already in the table above) or memorise
          three days. Cancelled flights also carry no delay label, so every delay figure elsewhere in this app is
          conditioned on the flight having left.
        </div>
      </div>
    </section>
  )
}

export function CancellationPanel() {
  const { data, loading } = useCancellations()
  if (loading) return <Skeleton className="h-40 w-full" />
  if (!data?.summary || !Array.isArray(data.by_signal)) return null
  return <CancellationBody c={data} />
}
