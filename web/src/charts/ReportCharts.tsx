/** Charts for the live model report card (Model route). Two series everywhere — the model (amber, slot 1) against the
 *  airline × hour baseline (teal, slot 2) — always with a legend and the 0.5 "coin flip" reference line, because an AUC
 *  chart without that anchor flatters the model. Thin slices are drawn but labelled `n` in the tooltip. */
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AXIS, CURSOR, Legend, TipBox } from './theme'
import { GRID, NEUTRAL, SERIES_1, SERIES_2 } from './tokens'
import { num } from '@/lib/time'
import type { LeadBucket, LiveDailyRow } from '@/lib/types'

const f3 = (x: number | null | undefined) => (x == null ? '—' : x.toFixed(3))
const COIN_FLIP = { model: 'model (XGBoost, live)', baseline: 'airline × hour baseline' }
const nf = (x: number | null | undefined) => (x == null ? 'no value' : x.toFixed(3))

/** Y range on round tenths that always keeps 0.5 in view but does not squash a 0.58 → 0.71 spread into nothing. */
function aucAxis(values: (number | null | undefined)[]): { domain: [number, number]; ticks: number[] } {
  const v = values.filter((x): x is number => x != null)
  const lo = Math.max(0, Math.floor(Math.min(0.45, ...v) * 10) / 10)
  const hi = Math.min(1, Math.ceil(Math.max(0.8, ...v) * 10) / 10)
  const ticks: number[] = []
  for (let t = lo; t <= hi + 1e-9; t += 0.1) ticks.push(Math.round(t * 10) / 10)
  return { domain: [lo, hi], ticks }
}

/** Daily AUC, model vs baseline. Days where nothing was late have no AUC and leave a gap — never a fabricated 0.5. */
export function DailyAuc({ rows }: { rows: LiveDailyRow[] }) {
  const data = rows.map((r) => ({
    date: r.date,
    n: r.n,
    thin: r.thin,
    partial: !!r.partial,
    rate: r.delayed15_rate,
    model: r.model.auc,
    baseline: r.baseline?.auc ?? null,
    mae: r.model.mae,
  }))
  const hasBaseline = data.some((d) => d.baseline != null)
  const axis = aucAxis(data.flatMap((d) => [d.model, d.baseline]))
  const partials = data.filter((d) => d.partial).map((d) => d.date.slice(5))
  return (
    <div
      role="img"
      aria-label={`Daily AUC, model versus airline by hour baseline. ${data
        .map(
          (d) => `${d.date}: model ${nf(d.model)}${hasBaseline ? `, baseline ${nf(d.baseline)}` : ''}, ${d.n} flights`,
        )
        .join('; ')}.`}
    >
      <Legend
        items={[
          { color: SERIES_1, label: COIN_FLIP.model, shape: 'line' },
          ...(hasBaseline ? [{ color: SERIES_2, label: COIN_FLIP.baseline, shape: 'line' as const }] : []),
          { color: NEUTRAL, label: 'coin flip (0.5)', shape: 'line' as const },
        ]}
      />
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -10 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="date" {...AXIS} tickFormatter={(d: string) => d.slice(5)} minTickGap={20} />
          <YAxis
            {...AXIS}
            width={44}
            domain={axis.domain}
            ticks={axis.ticks}
            tickFormatter={(v: number) => v.toFixed(1)}
          />
          <ReferenceLine y={0.5} stroke={NEUTRAL} strokeWidth={1} />
          <Tooltip
            cursor={CURSOR}
            content={({ active, payload }) => {
              const r = payload?.[0]?.payload as (typeof data)[number] | undefined
              if (!active || !r) return null
              return (
                <TipBox
                  title={r.date}
                  rows={[
                    ['model AUC', f3(r.model)],
                    ...(hasBaseline ? ([['baseline AUC', f3(r.baseline)]] as [string, string][]) : []),
                    ['model MAE', r.mae == null ? '—' : `${num(r.mae, 1)} min`],
                    ['flights', `${num(r.n)}${r.thin ? ' (thin)' : ''}${r.partial ? ' (partial day)' : ''}`],
                    ['were > 15 min late', r.rate == null ? '—' : `${Math.round(r.rate * 100)} %`],
                  ]}
                />
              )
            }}
          />
          <Line
            type="linear"
            dataKey="model"
            stroke={SERIES_1}
            strokeWidth={2}
            dot={{ r: 3, fill: SERIES_1, stroke: SERIES_1 }}
            connectNulls={false}
            isAnimationActive={false}
          />
          {hasBaseline && (
            <Line
              type="linear"
              dataKey="baseline"
              stroke={SERIES_2}
              strokeWidth={2}
              dot={{ r: 3, fill: SERIES_2, stroke: SERIES_2 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      {partials.length > 0 && (
        <p className="text-[0.7rem] text-muted mt-1 leading-relaxed">
          {partials.join(' and ')} {partials.length > 1 ? 'are' : 'is'} a partial day — the rolling window starts and
          ends part-way through a date, so those points cover fewer flights than a full day.
        </p>
      )}
    </div>
  )
}

/** AUC by forecast horizon (scheduled − scored). Bars from 0 with the coin-flip line marked; thin buckets are hatched
 *  rather than dropped, so a bar standing on 12 flights cannot be mistaken for a result. */
export function LeadBucketBars({ rows, thinAt }: { rows: LeadBucket[]; thinAt?: number }) {
  const data = rows.map((r) => ({
    label: r.label,
    n: r.n,
    thin: r.thin,
    rate: r.delayed15_rate,
    median: r.median_horizon_min ?? r.median_lead_min,
    model: r.model.auc,
    baseline: r.baseline?.auc ?? null,
    mae: r.model.mae,
  }))
  const hasBaseline = data.some((d) => d.baseline != null)
  const anyThin = data.some((d) => d.thin)
  return (
    <div
      role="img"
      aria-label={`AUC by forecast horizon. ${data
        .map(
          (d) => `${d.label}: model ${nf(d.model)}${hasBaseline ? `, baseline ${nf(d.baseline)}` : ''}, ${d.n} flights`,
        )
        .join('; ')}.`}
    >
      <Legend
        items={[
          { color: SERIES_1, label: COIN_FLIP.model },
          ...(hasBaseline ? [{ color: SERIES_2, label: COIN_FLIP.baseline }] : []),
          { color: NEUTRAL, label: 'coin flip (0.5)', shape: 'line' as const },
        ]}
      />
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -10 }} barCategoryGap="28%">
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="label" {...AXIS} />
          <YAxis
            {...AXIS}
            width={44}
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tickFormatter={(v: number) => v.toFixed(2)}
          />
          <ReferenceLine y={0.5} stroke={NEUTRAL} strokeWidth={1} />
          <Tooltip
            cursor={CURSOR}
            content={({ active, payload }) => {
              const r = payload?.[0]?.payload as (typeof data)[number] | undefined
              if (!active || !r) return null
              return (
                <TipBox
                  title={`last score ${r.label === 'after STD' ? 'after the scheduled time' : `${r.label} before the scheduled time`}`}
                  rows={[
                    ['model AUC', f3(r.model)],
                    ...(hasBaseline ? ([['baseline AUC', f3(r.baseline)]] as [string, string][]) : []),
                    ['model MAE', r.mae == null ? '—' : `${num(r.mae, 1)} min`],
                    ['flights', `${num(r.n)}${r.thin ? ' (thin — treat as noise)' : ''}`],
                    ['median horizon', r.median == null ? '—' : `${num(r.median)} min`],
                    ['were > 15 min late', r.rate == null ? '—' : `${Math.round(r.rate * 100)} %`],
                  ]}
                />
              )
            }}
          />
          <Bar dataKey="model" fill={SERIES_1} radius={[3, 3, 0, 0]} isAnimationActive={false} />
          {hasBaseline && <Bar dataKey="baseline" fill={SERIES_2} radius={[3, 3, 0, 0]} isAnimationActive={false} />}
        </BarChart>
      </ResponsiveContainer>
      <p className="text-[0.7rem] text-muted mt-1 leading-relaxed">
        n per bucket:{' '}
        {data.map((d, i) => (
          <span key={d.label} className="hk-num">
            {i > 0 && ' · '}
            {d.label} {num(d.n)}
            {d.thin ? ' (thin)' : ''}
          </span>
        ))}
        {anyThin && <span> — “thin” = under {num(thinAt ?? 100)} flights, where an AUC is mostly noise.</span>}
      </p>
    </div>
  )
}
