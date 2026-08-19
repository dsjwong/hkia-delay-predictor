import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AXIS, CURSOR, TipBox } from './theme'
import { GRID, INK_2, MUTED, SERIES_1 } from './tokens'

export interface HBarRow {
  label: string
  value: number
  n?: number
  extra?: [string, string][]
}

/** Horizontal ranked bars: one nominal series (slot 1), n as a direct label at the bar end, tooltip per bar. */
export function HBar({
  rows,
  fmt,
  height,
  xDomain,
  unit,
}: {
  rows: HBarRow[]
  fmt: (v: number) => string
  height?: number
  xDomain?: [number, number]
  unit?: string
}) {
  const h = height ?? Math.max(140, 26 * rows.length + 36)
  return (
    <ResponsiveContainer width="100%" height={h}>
      <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 56, bottom: 4, left: 4 }} barCategoryGap="30%">
        <CartesianGrid horizontal={false} stroke={GRID} />
        <XAxis
          type="number"
          {...AXIS}
          tickFormatter={fmt}
          domain={xDomain ?? [0, 'auto']}
          label={unit ? { value: unit, position: 'insideBottomRight', fill: MUTED, fontSize: 10, dy: 8 } : undefined}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={170}
          {...AXIS}
          tick={{ fill: INK_2, fontSize: 11 }}
          interval={0}
        />
        <Tooltip
          cursor={CURSOR}
          content={({ active, payload }) => {
            const r = payload?.[0]?.payload as HBarRow | undefined
            if (!active || !r) return null
            return (
              <TipBox
                title={r.label}
                rows={[
                  ['value', fmt(r.value)],
                  ...(r.n != null ? ([['n', r.n.toLocaleString()]] as [string, string][]) : []),
                  ...(r.extra ?? []),
                ]}
              />
            )
          }}
        />
        <Bar dataKey="value" fill={SERIES_1} radius={[0, 3, 3, 0]} isAnimationActive={false}>
          <LabelList
            dataKey="n"
            position="right"
            formatter={(v) => `n=${Number(v).toLocaleString()}`}
            style={{ fill: MUTED, fontSize: 10 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
