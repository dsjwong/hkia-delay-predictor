import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AXIS, Legend, TipBox } from './theme'
import { BLUE, GRID, ORANGE } from './tokens'
import { num, pct } from '@/lib/time'

export interface DailyRow {
  date: string
  n: number
  mean_delay: number
  pct15: number
  signal: number
  tc_name: string | null
}

/** Mean delay per day; TC-signal days as a second (emphasis) series so the legend names them. */
export function DailyBars({ rows }: { rows: DailyRow[] }) {
  const data = rows.map((r) => ({ ...r, normal: r.signal ? null : r.mean_delay, tc: r.signal ? r.mean_delay : null }))
  const hasTc = rows.some((r) => r.signal > 0)
  return (
    <div>
      <Legend
        items={[
          { color: BLUE, label: 'normal day' },
          ...(hasTc ? [{ color: ORANGE, label: 'TC signal in force' }] : []),
        ]}
      />
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -8 }} barCategoryGap="12%">
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="date" {...AXIS} tickFormatter={(d: string) => d.slice(5)} minTickGap={28} />
          <YAxis {...AXIS} width={44} tickFormatter={(v) => `${v}`} />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
            content={({ active, payload }) => {
              const r = payload?.[0]?.payload as DailyRow | undefined
              if (!active || !r) return null
              return (
                <TipBox
                  title={r.date}
                  rows={[
                    ['mean delay', `${num(r.mean_delay, 1)} min`],
                    ['> 15 min', pct(r.pct15)],
                    ['departures', num(r.n)],
                    ...(r.signal ? ([['TC signal', `${r.signal} ${r.tc_name ?? ''}`]] as [string, string][]) : []),
                  ]}
                />
              )
            }}
          />
          <Bar dataKey="normal" stackId="d" fill={BLUE} isAnimationActive={false} radius={[2, 2, 0, 0]} />
          <Bar dataKey="tc" stackId="d" fill={ORANGE} isAnimationActive={false} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Small multiple: share delayed > 15 min by hour for one airline (same hue everywhere — magnitude, not identity). */
export function HourShare({ pct15, n }: { pct15: (number | null)[]; n: number[] }) {
  const data = pct15.map((p, h) => ({ hour: h, p, n: n[h] ?? 0 }))
  return (
    <ResponsiveContainer width="100%" height={150}>
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -6 }} barCategoryGap="20%">
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="hour" {...AXIS} ticks={[0, 6, 12, 18, 23]} tickFormatter={(h) => String(h).padStart(2, '0')} />
        <YAxis
          domain={[0, 1]}
          {...AXIS}
          width={42}
          tickFormatter={(v) => `${Math.round(v * 100)}%`}
          ticks={[0, 0.5, 1]}
        />
        <Tooltip
          cursor={{ fill: 'rgba(255,255,255,0.04)' }}
          content={({ active, payload }) => {
            const r = payload?.[0]?.payload as { hour: number; p: number | null; n: number } | undefined
            if (!active || !r) return null
            return (
              <TipBox
                title={`${String(r.hour).padStart(2, '0')}:00`}
                rows={[
                  ['> 15 min', pct(r.p)],
                  ['n', String(r.n)],
                ]}
              />
            )
          }}
        />
        <Bar dataKey="p" fill={BLUE} isAnimationActive={false} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
