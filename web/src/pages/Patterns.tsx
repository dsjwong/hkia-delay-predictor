import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Tile } from '@/components/ui/tile'
import { Segmented } from '@/components/ui/segmented'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Empty } from '@/components/ui/empty'
import { SkeletonCard } from '@/components/ui/skeleton'
import { Heatmap } from '@/charts/Heatmap'
import { HBar } from '@/charts/HBar'
import { DailyBars, HourShare } from '@/charts/PatternCharts'
import { usePatterns } from '@/lib/data'
import { num, pct } from '@/lib/time'

function PageSkeleton() {
  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <div className="hk-skeleton h-6 w-64" />
        <div className="hk-skeleton h-3.5 w-96" />
      </div>
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <Tile key={i} label=" " value="" loading />
        ))}
      </div>
      <SkeletonCard body="h-56" />
      <div className="grid gap-4 lg:grid-cols-2">
        <SkeletonCard body="h-80" />
        <SkeletonCard body="h-80" />
      </div>
    </div>
  )
}

export default function Patterns() {
  const { data: p, error, loading } = usePatterns()
  const [metric, setMetric] = useState<'mean' | 'pct'>('mean')
  const [showTables, setShowTables] = useState(false)
  if (error) return <Empty tone="error" className="py-16" title="Could not load patterns.json" detail={error} />
  if (loading || !p) return <PageSkeleton />
  if (!p.summary || !p.heatmap)
    return (
      <Empty
        className="py-16"
        title="No departed flights in the window yet."
        detail="Patterns appear once the ingest has a few days of departures."
      />
    )
  const s = p.summary
  const airlines = (p.airlines ?? []).slice(0, 15).map((a) => ({
    label: `${a.name} (${a.code})`,
    value: a.pct15,
    n: a.n,
    extra: [['mean delay', `${num(a.mean_delay, 1)} min`]] as [string, string][],
  }))
  const dests = (p.destinations ?? []).slice(0, 15).map((d) => ({
    label: d.city && d.city !== d.code ? `${d.city} (${d.code})` : d.code,
    value: d.mean_delay,
    n: d.n,
    extra: [['> 15 min', pct(d.pct15)]] as [string, string][],
  }))
  const ty = p.typhoon
  const Chevron = showTables ? ChevronDown : ChevronRight
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">Delay patterns — last {s.window_days} days</h2>
        <p className="text-xs text-muted mt-1">
          Rolling window kept by the data.gov.hk API; delays clipped to [-60, 600] min like the training set; cancelled
          flights excluded. {s.date_min} → {s.date_max}.
        </p>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        <Tile label="Departed flights" value={num(s.n)} sub={`${s.date_min} → ${s.date_max}`} />
        <Tile
          label="Mean delay"
          value={`${num(s.mean_delay, 1)} min`}
          sub={`median ${num(s.median_delay)} min`}
          hint="Delays are heavy-tailed: the median is far below the mean."
        />
        <Tile label="Delayed > 15 min" value={pct(s.pct15)} sub="share of departures" tone="accent" />
        <Tile label="Airlines" value={s.n_airlines} sub={`${s.n_dest} destinations`} />
      </div>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>
              {metric === 'mean' ? 'Mean delay (min)' : 'Share delayed > 15 min'} by scheduled hour (HKT) × weekday
            </CardTitle>
            <CardDescription>hover or focus a cell for the value and n</CardDescription>
          </div>
          <Segmented
            value={metric}
            onChange={setMetric}
            label="Heatmap metric"
            options={[
              { value: 'mean', label: 'Mean delay' },
              { value: 'pct', label: '% > 15 min' },
            ]}
          />
        </CardHeader>
        <CardContent>
          <Heatmap
            dow={p.heatmap.dow}
            hours={p.heatmap.hours}
            values={metric === 'mean' ? p.heatmap.mean_delay : p.heatmap.pct15}
            counts={p.heatmap.n}
            isMean={metric === 'mean'}
          />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Airlines — share delayed &gt; 15 min</CardTitle>
              <CardDescription>top 15 by share, n ≥ 50 departures</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <HBar rows={airlines} fmt={(v) => `${Math.round(v * 100)}%`} xDomain={[0, 1]} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Top 15 destinations by flights — mean delay</CardTitle>
              <CardDescription>minutes</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <HBar rows={dests} fmt={(v) => `${Math.round(v)}`} unit="min" />
          </CardContent>
        </Card>
      </div>

      <Card>
        <div className="px-2 py-1.5">
          <Button variant="ghost" size="sm" onClick={() => setShowTables((v) => !v)} aria-expanded={showTables}>
            <Chevron size={14} aria-hidden="true" />
            {showTables ? 'Hide' : 'Show'} tables — every airline (n ≥ 50) and the top 25 destinations
          </Button>
        </div>
        {showTables && (
          <div className="grid gap-4 lg:grid-cols-2 px-4 pb-4">
            <div className="rounded-lg border border-border overflow-auto max-h-[480px]">
              <table className="hk-table">
                <thead>
                  <tr>
                    <th>Airline</th>
                    <th className="text-right">n</th>
                    <th className="text-right">mean (min)</th>
                    <th className="text-right">&gt; 15 min</th>
                  </tr>
                </thead>
                <tbody>
                  {(p.airlines ?? []).map((a) => (
                    <tr key={a.code}>
                      <td>
                        {a.name} <span className="text-muted">({a.code})</span>
                      </td>
                      <td className="hk-num text-right">{num(a.n)}</td>
                      <td className="hk-num text-right">{num(a.mean_delay, 1)}</td>
                      <td className="hk-num text-right">{pct(a.pct15)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="rounded-lg border border-border overflow-auto max-h-[480px]">
              <table className="hk-table">
                <thead>
                  <tr>
                    <th>Destination</th>
                    <th className="text-right">n</th>
                    <th className="text-right">mean (min)</th>
                    <th className="text-right">&gt; 15 min</th>
                  </tr>
                </thead>
                <tbody>
                  {(p.destinations ?? []).map((d) => (
                    <tr key={d.code}>
                      <td>
                        {d.city} <span className="text-muted">({d.code})</span>
                      </td>
                      <td className="hk-num text-right">{num(d.n)}</td>
                      <td className="hk-num text-right">{num(d.mean_delay, 1)}</td>
                      <td className="hk-num text-right">{pct(d.pct15)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Card>

      {p.by_hour_top_airlines && (
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Share delayed &gt; 15 min by hour — top 4 airlines</CardTitle>
              <CardDescription>same scale in every panel</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {Object.entries(p.by_hour_top_airlines).map(([code, v]) => (
                <div key={code}>
                  <div className="text-xs text-ink-2 mb-1">
                    {v.name} <span className="text-muted">({code})</span>
                  </div>
                  <HourShare pct15={v.pct15} n={v.n} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {ty && (
        <div className="hk-card border-warning/40 px-4 py-3 text-sm text-ink-2 leading-relaxed">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="warn" dot>
              typhoon days
            </Badge>
            <span className="font-semibold text-ink">{ty.n_days} day(s) with a tropical-cyclone signal in force</span>
          </div>
          ({ty.names.join(', ')}: {ty.days.map((d) => `${d.date} sig ${d.signal}`).join(', ')}): mean delay{' '}
          <b className="text-ink">{num(ty.mean_delay)} min</b>, {pct(ty.pct15)} &gt; 15 min, vs{' '}
          <b className="text-ink">{num(ty.mean_delay_other)} min</b>, {pct(ty.pct15_other)} on the other {ty.n_other}{' '}
          days.
          {ty.signal8_mean_delay != null &&
            ` Signal 8+ days only: mean ${num(ty.signal8_mean_delay)} min (${ty.signal8_days.join(', ')}).`}{' '}
          Handful of days — anecdotal, not a measured effect.
        </div>
      )}

      {p.daily && (
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Mean departure delay per day</CardTitle>
              <CardDescription>minutes; TC-signal days highlighted</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <DailyBars rows={p.daily} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
