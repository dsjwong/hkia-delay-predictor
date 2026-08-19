import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AXIS, CURSOR, CURSOR_LINE, GRID_PROPS, Legend, TipBox } from './theme'
import { CARD, NEUTRAL, SERIES_1, SERIES_2 } from './tokens'
import type { Flight } from '@/lib/types'
import { hm, minuteOfDayHKT, pct, signed } from '@/lib/time'

interface Pt {
  x: number
  y: number
  f: Flight
}

const hhmm = (m: number) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`

/** Strip of scored flights: scheduled time (x) vs P(delay > 15) (y); departed vs pending as two categorical series. */
export function Timeline({
  flights,
  onPick,
  names,
}: {
  flights: Flight[]
  onPick?: (f: Flight) => void
  names: (code: string | null) => string
}) {
  const pts = (st: 'departed' | 'scheduled'): Pt[] =>
    flights
      .filter((f) => f.p != null && f.status === st)
      .map((f) => ({ x: minuteOfDayHKT(f.sched_ts), y: f.p as number, f }))
  const dep = pts('departed')
  const sch = pts('scheduled')
  const dot = (fill: string) => (p: { cx?: number; cy?: number }) => (
    <circle cx={p.cx} cy={p.cy} r={4.5} fill={fill} stroke={CARD} strokeWidth={1.5} style={{ cursor: 'pointer' }} />
  )
  return (
    <div>
      <Legend
        items={[
          { color: SERIES_1, label: 'departed', shape: 'dot' },
          { color: SERIES_2, label: 'not yet departed', shape: 'dot' },
        ]}
      />
      <ResponsiveContainer width="100%" height={260}>
        <ScatterChart margin={{ top: 8, right: 12, bottom: 4, left: -4 }}>
          <CartesianGrid {...GRID_PROPS} />
          <XAxis
            type="number"
            dataKey="x"
            domain={[0, 1440]}
            ticks={[0, 180, 360, 540, 720, 900, 1080, 1260, 1440]}
            tickFormatter={hhmm}
            {...AXIS}
            name="scheduled (HKT)"
          />
          <YAxis
            type="number"
            dataKey="y"
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            {...AXIS}
            width={46}
          />
          <ReferenceLine y={0.5} stroke={NEUTRAL} />
          <Tooltip
            cursor={CURSOR_LINE}
            content={({ active, payload }) => {
              const p = payload?.[0]?.payload as Pt | undefined
              if (!active || !p) return null
              const f = p.f
              return (
                <TipBox
                  title={`${f.flight_no} → ${f.dest} · ${names(f.airline)}`}
                  rows={[
                    ['scheduled', hm(f.sched_ts)],
                    ['actual', hm(f.actual_ts)],
                    ['P(delay > 15)', pct(f.p)],
                    ['predicted', f.pred_min == null ? '—' : `${Math.round(f.pred_min)} min`],
                    ...(f.delay_min != null
                      ? ([['actual delay', `${signed(f.delay_min)} min`]] as [string, string][])
                      : []),
                  ]}
                />
              )
            }}
          />
          <Scatter
            name="departed"
            data={dep}
            fill={SERIES_1}
            shape={dot(SERIES_1)}
            onClick={(d) => onPick?.((d as unknown as Pt).f)}
            cursor="pointer"
            isAnimationActive={false}
          />
          <Scatter
            name="not yet departed"
            data={sch}
            fill={SERIES_2}
            shape={dot(SERIES_2)}
            onClick={(d) => onPick?.((d as unknown as Pt).f)}
            cursor="pointer"
            isAnimationActive={false}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

export interface HourRow {
  hour: number
  n: number
  p: number | null
  n_dep: number
  obs: number | null
}

/** Grouped bars per scheduled hour: predicted mean P vs observed late share. */
export function HourlyBars({ rows }: { rows: HourRow[] }) {
  return (
    <div>
      <Legend
        items={[
          { color: SERIES_1, label: 'predicted mean P(delay > 15)' },
          { color: SERIES_2, label: 'observed share > 15 min (departed)' },
        ]}
      />
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: -4 }} barCategoryGap="22%" barGap={2}>
          <CartesianGrid {...GRID_PROPS} />
          <XAxis dataKey="hour" {...AXIS} tickFormatter={(h) => String(h).padStart(2, '0')} interval={1} />
          <YAxis
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            {...AXIS}
            width={46}
          />
          <Tooltip
            cursor={CURSOR}
            content={({ active, payload }) => {
              const r = payload?.[0]?.payload as HourRow | undefined
              if (!active || !r) return null
              return (
                <TipBox
                  title={`${String(r.hour).padStart(2, '0')}:00 HKT`}
                  rows={[
                    ['predicted', `${pct(r.p)} · ${r.n} flights`],
                    ['observed', `${pct(r.obs)} · ${r.n_dep} departed`],
                  ]}
                />
              )
            }}
          />
          <Bar dataKey="p" name="predicted" fill={SERIES_1} isAnimationActive={false} radius={[3, 3, 0, 0]} />
          <Bar dataKey="obs" name="observed" fill={SERIES_2} isAnimationActive={false} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
