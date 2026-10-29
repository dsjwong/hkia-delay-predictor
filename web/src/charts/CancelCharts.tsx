/** Cancelled-departure charts. One series per chart, in `critical` red — the app-wide "cancelled" meaning (docs/design.md) —
 *  and never beside the amber P(delay) series. Thin cells are labelled with their n rather than hidden. */
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AXIS, CURSOR, TipBox } from './theme'
import { CRITICAL, GRID } from './tokens'
import { num, pct } from '@/lib/time'
import type { CancelCell } from '@/lib/types'

/** Rate of departures cancelled by scheduled clock hour (HKT), ordinary days only. */
export function CancelByHour({ rows, height = 190 }: { rows: (CancelCell & { hour: number })[]; height?: number }) {
  const data = rows.filter((r) => r.n >= 100).map((r) => ({ ...r, label: String(r.hour).padStart(2, '0') }))
  const label = `Cancellation rate by scheduled hour on ordinary days: ${data
    .map((d) => `${d.label}h ${pct(d.rate, 2)}`)
    .join(', ')}`
  return (
    <div role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 6, right: 8, bottom: 4, left: 0 }} barCategoryGap="18%">
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey="label" {...AXIS} interval={1} />
          <YAxis {...AXIS} width={44} tickFormatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
          <Tooltip
            cursor={CURSOR}
            content={({ active, payload }) => {
              const r = payload?.[0]?.payload as (CancelCell & { label: string }) | undefined
              if (!active || !r) return null
              return (
                <TipBox
                  title={`${r.label}:00 HKT`}
                  rows={[
                    ['cancelled', `${num(r.n_cancelled)} of ${num(r.n)}`],
                    ['rate', pct(r.rate, 2)],
                    ['95 % CI', r.ci ? `${pct(r.ci[0], 2)} – ${pct(r.ci[1], 2)}` : '—'],
                  ]}
                />
              )
            }}
          />
          <Bar dataKey="rate" fill={CRITICAL} radius={[3, 3, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
