/** Charts for the Typhoon Noul case study (/typhoon).
 *
 * Design decisions worth keeping (docs/design.md):
 *  - ONE y-axis on the centrepiece. The TC signal is not a second scale — it is drawn as a labelled background band
 *    behind the delay bars, so the reader decodes the level from the T1/T3/T8/T9 chip rather than from a tint. That
 *    is the mandated secondary encoding for a colour difference too small to read (see SIGNAL_BAND in lib/theme.ts).
 *  - The gust line and the cancellations strip get their own panels with their own axes, aligned on the same hours,
 *    instead of riding a second axis on the main chart.
 *  - Amber (SERIES_1) = delay, teal (SERIES_2) = wind, critical red = cancelled — the app-wide meanings. Amber and
 *    red are near-indistinguishable under deuteranopia (validator: ΔE 4.4), so they are never plotted in one chart;
 *    each panel carries a single series and a title that names it.
 */
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AXIS, CURSOR, Legend, TipBox } from './theme'
import { CRITICAL, GRID, MUTED, NEUTRAL, SERIES_1, SERIES_2, SIGNAL_BAND } from './tokens'
import type { CaseHour } from '@/lib/types'
import { num } from '@/lib/time'

/** '2026-07-26T08:00:00+08:00' -> '26 08:00'; the label the x-axis and every tooltip title use. */
export function hourLabel(t: string): string {
  return `${t.slice(8, 10)} ${t.slice(11, 16)}`
}
const dayTick = (t: string) => (t.slice(11, 13) === '00' ? `Jul ${t.slice(8, 10)}` : t.slice(11, 16))

/** Explicit ticks every `everyH` hours — recharts' `interval` counts categories, which gets unreadable on a
 *  120-hour band chart and worse again in the half-width panels underneath. */
function hourTicks(hours: CaseHour[], everyH: number): string[] {
  return hours.filter((h) => Number(h.t.slice(11, 13)) % everyH === 0).map((h) => h.t)
}

/** Rounded [lo, hi] for the delay axis: multiples of 60 min, always including 0, headroom for the band labels. */
export function delayDomain(hours: CaseHour[]): [number, number] {
  const vals = hours.map((h) => h.mean_delay).filter((v): v is number => v != null)
  const lo = Math.min(0, ...vals)
  const hi = Math.max(0, ...vals)
  return [Math.min(0, Math.floor(lo / 30) * 30), Math.max(60, Math.ceil((hi * 1.1) / 60) * 60)]
}

/** Round ticks across the delay domain, always including 0 so "on time" is anchored. */
export function delayTicks([lo, hi]: [number, number]): number[] {
  const step = hi >= 480 ? 120 : hi >= 240 ? 60 : 30
  const out: number[] = []
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) out.push(v)
  return out.includes(0) ? out : [lo, ...out]
}

/** Contiguous runs of the same signal level, as index ranges into `hours` — one ReferenceArea each. */
export function signalRuns(hours: CaseHour[]): { signal: number; from: string; to: string; n: number }[] {
  const out: { signal: number; from: string; to: string; n: number }[] = []
  for (const h of hours) {
    const last = out[out.length - 1]
    if (last && last.signal === h.signal) {
      last.to = h.t
      last.n += 1
    } else {
      out.push({ signal: h.signal, from: h.t, to: h.t, n: 1 })
    }
  }
  return out.filter((r) => r.signal > 0)
}

function TipHour({ h }: { h: CaseHour }) {
  return (
    <TipBox
      title={`${hourLabel(h.t)} HKT${h.signal ? ` · signal ${h.signal}` : ''}`}
      rows={[
        ['mean delay', h.mean_delay == null ? '—' : `${num(h.mean_delay)} min`],
        ['p90 delay', h.p90_delay == null ? '—' : `${num(h.p90_delay)} min`],
        ['departed / scheduled', `${h.n_departed} / ${h.n_sched}`],
        ['cancelled', String(h.n_cancelled)],
        ['wind · gust', `${num(h.wspd_kt)} · ${num(h.wgst_kt)} kt`],
        ['visibility · cat', `${h.visib_sm == null ? '—' : h.visib_sm.toFixed(1) + ' sm'} · ${h.flt_cat ?? '—'}`],
      ]}
    />
  )
}

/** Centrepiece: hourly mean delay as bars, TC signal as labelled background bands. One y-axis, minutes. */
export function DelayWithSignalBands({ hours, height = 300 }: { hours: CaseHour[]; height?: number }) {
  const runs = signalRuns(hours)
  const [bottom, top] = delayDomain(hours)
  const ticks = hourTicks(hours, 6)
  const yTicks = delayTicks([bottom, top])
  return (
    <div>
      <Legend
        items={[
          { color: SERIES_1, label: 'mean departure delay (min)' },
          { color: 'rgba(250,250,250,0.10)', label: 'typhoon signal in force', shape: 'square' },
        ]}
      />
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={hours} margin={{ top: 16, right: 8, bottom: 4, left: -10 }} barCategoryGap="8%">
          <CartesianGrid stroke={GRID} vertical={false} />
          {runs.map((r) => (
            <ReferenceArea
              key={r.from}
              x1={r.from}
              x2={r.to}
              y1={bottom}
              y2={top}
              fill={SIGNAL_BAND[r.signal] ?? SIGNAL_BAND[1]}
              stroke={GRID}
              ifOverflow="extendDomain"
              label={{
                value: r.n >= 2 ? `T${r.signal}` : '',
                position: 'insideTop',
                fill: MUTED,
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: '0.04em',
              }}
            />
          ))}
          <XAxis dataKey="t" {...AXIS} tickFormatter={dayTick} ticks={ticks} minTickGap={16} />
          <YAxis
            {...AXIS}
            width={46}
            domain={[bottom, top]}
            ticks={yTicks}
            allowDataOverflow
            tickFormatter={(v) => `${v}`}
          />
          <Tooltip
            cursor={CURSOR}
            content={({ active, payload }) => {
              const h = payload?.[0]?.payload as CaseHour | undefined
              return active && h ? <TipHour h={h} /> : null
            }}
          />
          <Bar dataKey="mean_delay" fill={SERIES_1} isAnimationActive={false} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Wind sparkline under the centrepiece: sustained wind + gust, own panel, own axis (knots). */
export function GustPanel({ hours, height = 110 }: { hours: CaseHour[]; height?: number }) {
  const ticks = hourTicks(hours, 12)
  return (
    <div>
      <Legend
        items={[
          { color: SERIES_2, label: 'gust (kt)', shape: 'line' },
          { color: NEUTRAL, label: 'sustained wind (kt)', shape: 'line' },
        ]}
      />
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={hours} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="t" {...AXIS} tickFormatter={dayTick} ticks={ticks} minTickGap={12} />
          <YAxis {...AXIS} width={46} tickFormatter={(v) => `${v}`} />
          <Tooltip
            cursor={false}
            content={({ active, payload }) => {
              const h = payload?.[0]?.payload as CaseHour | undefined
              if (!active || !h) return null
              return (
                <TipBox
                  title={`${hourLabel(h.t)} HKT`}
                  rows={[
                    ['gust', `${num(h.wgst_kt)} kt`],
                    ['wind', `${num(h.wspd_kt)} kt`],
                    ['visibility', h.visib_sm == null ? '—' : `${h.visib_sm.toFixed(1)} sm`],
                    ['category', h.flt_cat ?? '—'],
                  ]}
                />
              )
            }}
          />
          <Line dataKey="wspd_kt" stroke={NEUTRAL} strokeWidth={1.25} dot={false} isAnimationActive={false} />
          <Line dataKey="wgst_kt" stroke={SERIES_2} strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Cancellations per hour: own panel, own axis (flights). Red = cancelled, the app-wide meaning. */
export function CancelStrip({ hours, height = 110 }: { hours: CaseHour[]; height?: number }) {
  const ticks = hourTicks(hours, 12)
  return (
    <div>
      <Legend items={[{ color: CRITICAL, label: 'departures cancelled' }]} />
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={hours} margin={{ top: 4, right: 8, bottom: 0, left: -10 }} barCategoryGap="8%">
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="t" {...AXIS} tickFormatter={dayTick} ticks={ticks} minTickGap={12} />
          <YAxis {...AXIS} width={46} allowDecimals={false} />
          <Tooltip
            cursor={CURSOR}
            content={({ active, payload }) => {
              const h = payload?.[0]?.payload as CaseHour | undefined
              if (!active || !h) return null
              return (
                <TipBox
                  title={`${hourLabel(h.t)} HKT`}
                  rows={[
                    ['cancelled', String(h.n_cancelled)],
                    ['scheduled', String(h.n_sched)],
                    ['departed', String(h.n_departed)],
                  ]}
                />
              )
            }}
          />
          <Bar dataKey="n_cancelled" fill={CRITICAL} isAnimationActive={false} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export interface SignalTotalRow {
  signal: number
  mean_delay: number | null
  pred_delay: number | null
  n: number
}

/** Retrospective: what the model said the delay would be vs what it was, per signal level. Two series, legend. */
export function PredVsObsBySignal({ rows, height = 220 }: { rows: SignalTotalRow[]; height?: number }) {
  return (
    <div>
      <Legend
        items={[
          { color: SERIES_1, label: 'model, predicted delay (in-sample)' },
          { color: SERIES_2, label: 'observed delay' },
        ]}
      />
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: -10 }} barCategoryGap="24%" barGap={2}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="signal" {...AXIS} tickFormatter={(s: number) => (s ? `T${s}` : 'none')} />
          <YAxis {...AXIS} width={46} />
          <Tooltip
            cursor={CURSOR}
            content={({ active, payload }) => {
              const r = payload?.[0]?.payload as SignalTotalRow | undefined
              if (!active || !r) return null
              return (
                <TipBox
                  title={r.signal ? `Signal ${r.signal}` : 'No signal'}
                  rows={[
                    ['predicted (in-sample)', `${num(r.pred_delay)} min`],
                    ['observed', `${num(r.mean_delay)} min`],
                    ['flights', String(r.n)],
                  ]}
                />
              )
            }}
          />
          <Bar dataKey="pred_delay" fill={SERIES_1} isAnimationActive={false} radius={[2, 2, 0, 0]} />
          <Bar dataKey="mean_delay" fill={SERIES_2} isAnimationActive={false} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
