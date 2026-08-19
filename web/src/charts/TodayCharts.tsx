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
import { AXIS, Legend, TipBox } from './theme'
import { BLUE, GRID, ORANGE } from './tokens'
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
  return (
    <div>
      <Legend
        items={[
          { color: BLUE, label: 'departed', shape: 'dot' },
          { color: ORANGE, label: 'not yet departed', shape: 'dot' },
        ]}
      />
      <ResponsiveContainer width="100%" height={260}>
        <ScatterChart margin={{ top: 8, right: 12, bottom: 4, left: -4 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
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
          <ReferenceLine y={0.5} stroke={GRID} />
          <Tooltip
            cursor={{ strokeDasharray: undefined, stroke: GRID }}
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
            fill={BLUE}
            stroke="#0b1220"
            strokeWidth={1}
            r={4}
            onClick={(d) => onPick?.((d as unknown as Pt).f)}
            cursor="pointer"
            isAnimationActive={false}
          />
          <Scatter
            name="not yet departed"
            data={sch}
            fill={ORANGE}
            stroke="#0b1220"
            strokeWidth={1}
            r={4}
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
          { color: BLUE, label: 'predicted mean P(delay > 15)' },
          { color: ORANGE, label: 'observed share > 15 min (departed)' },
        ]}
      />
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: -4 }} barCategoryGap="18%" barGap={1}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="hour" {...AXIS} tickFormatter={(h) => String(h).padStart(2, '0')} interval={1} />
          <YAxis
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            {...AXIS}
            width={46}
          />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
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
          <Bar dataKey="p" name="predicted" fill={BLUE} isAnimationActive={false} radius={[2, 2, 0, 0]} />
          <Bar dataKey="obs" name="observed" fill={ORANGE} isAnimationActive={false} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
