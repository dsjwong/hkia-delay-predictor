import { useState } from 'react'
import { Tile } from '@/components/ui/tile'
import { Segmented } from '@/components/ui/segmented'
import { Heatmap } from '@/charts/Heatmap'
import { HBar } from '@/charts/HBar'
import { DailyBars, HourShare } from '@/charts/PatternCharts'
import { ChartHead } from '@/charts/theme'
import { usePatterns } from '@/lib/data'
import { num, pct } from '@/lib/time'

export default function Patterns() {
  const { data: p, error, loading } = usePatterns()
  const [metric, setMetric] = useState<'mean' | 'pct'>('mean')
  const [showTables, setShowTables] = useState(false)
  if (error) return <div className="text-sm text-critical">Could not load patterns.json: {error}</div>
  if (loading || !p) return <div className="text-sm text-muted">Loading…</div>
  if (!p.summary || !p.heatmap) return <div className="text-sm text-muted">No departed flights in the window yet.</div>
  const s = p.summary
  const airlines = (p.airlines ?? [])
    .slice(0, 15)
    .map((a) => ({
      label: `${a.name} (${a.code})`,
      value: a.pct15,
      n: a.n,
      extra: [['mean delay', `${num(a.mean_delay, 1)} min`]] as [string, string][],
    }))
  const dests = (p.destinations ?? [])
    .slice(0, 15)
    .map((d) => ({
      label: d.city && d.city !== d.code ? `${d.city} (${d.code})` : d.code,
      value: d.mean_delay,
      n: d.n,
      extra: [['> 15 min', pct(d.pct15)]] as [string, string][],
    }))
  const ty = p.typhoon
  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold">Delay patterns — last {s.window_days} days</h2>
        <p className="text-xs text-muted">
          Rolling window kept by the data.gov.hk API; delays clipped to [-60, 600] min like the training set; cancelled
          flights excluded. {s.date_min} → {s.date_max}.
        </p>
      </div>
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-2">
        <Tile label="Departed flights" value={num(s.n)} sub={`${s.date_min} → ${s.date_max}`} />
        <Tile
          label="Mean delay"
          value={`${num(s.mean_delay, 1)} min`}
          sub={`median ${num(s.median_delay)} min`}
          hint="Delays are heavy-tailed: the median is far below the mean."
        />
        <Tile label="Delayed > 15 min" value={pct(s.pct15)} sub="share of departures" />
        <Tile label="Airlines" value={s.n_airlines} sub={`${s.n_dest} destinations`} />
      </div>

      <div className="hk-card p-3">
        <ChartHead
          title={`${metric === 'mean' ? 'Mean delay (min)' : 'Share delayed > 15 min'} by scheduled hour (HKT) × weekday`}
          right={
            <Segmented
              value={metric}
              onChange={setMetric}
              label="Heatmap metric"
              options={[
                { value: 'mean', label: 'Mean delay' },
                { value: 'pct', label: '% > 15 min' },
              ]}
            />
          }
        />
        <Heatmap
          dow={p.heatmap.dow}
          hours={p.heatmap.hours}
          values={metric === 'mean' ? p.heatmap.mean_delay : p.heatmap.pct15}
          counts={p.heatmap.n}
          isMean={metric === 'mean'}
        />
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="hk-card p-3">
          <ChartHead title="Airlines — share delayed > 15 min" sub="top 15 by share, n ≥ 50 departures" />
          <HBar rows={airlines} fmt={(v) => `${Math.round(v * 100)}%`} xDomain={[0, 1]} />
        </div>
        <div className="hk-card p-3">
          <ChartHead title="Top 15 destinations by flights — mean delay" sub="minutes" />
          <HBar rows={dests} fmt={(v) => `${Math.round(v)}`} unit="min" />
        </div>
      </div>

      <div className="hk-card p-3">
        <button
          className="text-sm text-accent cursor-pointer"
          onClick={() => setShowTables((v) => !v)}
          aria-expanded={showTables}
        >
          {showTables ? 'Hide' : 'Show'} tables — every airline (n ≥ 50) and the top 25 destinations
        </button>
        {showTables && (
          <div className="grid gap-3 lg:grid-cols-2 mt-2">
            <table className="w-full text-sm">
              <thead>
                <tr className="hk-kicker text-left border-b border-border">
                  <th className="py-1 font-normal">Airline</th>
                  <th className="py-1 font-normal">n</th>
                  <th className="py-1 font-normal">mean (min)</th>
                  <th className="py-1 font-normal">&gt; 15 min</th>
                </tr>
              </thead>
              <tbody>
                {(p.airlines ?? []).map((a) => (
                  <tr key={a.code} className="border-b border-border/50">
                    <td className="py-0.5">
                      {a.name} <span className="text-muted">({a.code})</span>
                    </td>
                    <td className="py-0.5 hk-num">{num(a.n)}</td>
                    <td className="py-0.5 hk-num">{num(a.mean_delay, 1)}</td>
                    <td className="py-0.5 hk-num">{pct(a.pct15)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <table className="w-full text-sm">
              <thead>
                <tr className="hk-kicker text-left border-b border-border">
                  <th className="py-1 font-normal">Destination</th>
                  <th className="py-1 font-normal">n</th>
                  <th className="py-1 font-normal">mean (min)</th>
                  <th className="py-1 font-normal">&gt; 15 min</th>
                </tr>
              </thead>
              <tbody>
                {(p.destinations ?? []).map((d) => (
                  <tr key={d.code} className="border-b border-border/50">
                    <td className="py-0.5">
                      {d.city} <span className="text-muted">({d.code})</span>
                    </td>
                    <td className="py-0.5 hk-num">{num(d.n)}</td>
                    <td className="py-0.5 hk-num">{num(d.mean_delay, 1)}</td>
                    <td className="py-0.5 hk-num">{pct(d.pct15)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {p.by_hour_top_airlines && (
        <div className="hk-card p-3">
          <ChartHead title="Share delayed > 15 min by hour — top 4 airlines" sub="same scale in every panel" />
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {Object.entries(p.by_hour_top_airlines).map(([code, v]) => (
              <div key={code}>
                <div className="text-xs text-ink-2 mb-1">
                  {v.name} <span className="text-muted">({code})</span>
                </div>
                <HourShare pct15={v.pct15} n={v.n} />
              </div>
            ))}
          </div>
        </div>
      )}

      {ty && (
        <div className="hk-card p-3 border-warning/50">
          <div className="text-sm">
            <span className="font-semibold">Typhoon days in the window</span> — {ty.n_days} day(s) with a
            tropical-cyclone signal in force ({ty.names.join(', ')}:{' '}
            {ty.days.map((d) => `${d.date} sig ${d.signal}`).join(', ')}): mean delay <b>{num(ty.mean_delay)} min</b>,{' '}
            {pct(ty.pct15)} &gt; 15 min, vs <b>{num(ty.mean_delay_other)} min</b>, {pct(ty.pct15_other)} on the other{' '}
            {ty.n_other} days.
            {ty.signal8_mean_delay != null &&
              ` Signal 8+ days only: mean ${num(ty.signal8_mean_delay)} min (${ty.signal8_days.join(', ')}).`}{' '}
            Handful of days — anecdotal, not a measured effect.
          </div>
        </div>
      )}
      {p.daily && (
        <div className="hk-card p-3">
          <ChartHead title="Mean departure delay per day" sub="minutes; TC-signal days highlighted" />
          <DailyBars rows={p.daily} />
        </div>
      )}
    </div>
  )
}
