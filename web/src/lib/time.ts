/** All times are shown in HKT (UTC+8). */
export const HKT = 'Asia/Hong_Kong'

const fmtHM = new Intl.DateTimeFormat('en-GB', { timeZone: HKT, hour: '2-digit', minute: '2-digit', hour12: false })
const fmtHMS = new Intl.DateTimeFormat('en-GB', {
  timeZone: HKT,
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
})
const fmtDate = new Intl.DateTimeFormat('en-GB', {
  timeZone: HKT,
  weekday: 'short',
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})
const fmtDT = new Intl.DateTimeFormat('en-GB', {
  timeZone: HKT,
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

export function toDate(ts: string | number | null | undefined): Date | null {
  if (ts == null) return null
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts)
  return Number.isNaN(d.getTime()) ? null : d
}
export function hm(ts: string | number | null | undefined): string {
  const d = toDate(ts)
  return d ? fmtHM.format(d) : '—'
}
export function hms(ts: string | number | Date | null | undefined): string {
  const d = ts instanceof Date ? ts : toDate(ts)
  return d ? fmtHMS.format(d) : '—'
}
export function dateLong(ts: string | null | undefined): string {
  const d = ts ? new Date(ts.length === 10 ? ts + 'T00:00:00+08:00' : ts) : null
  return d && !Number.isNaN(d.getTime()) ? fmtDate.format(d) : '—'
}
export function dt(ts: string | null | undefined): string {
  const d = toDate(ts)
  return d ? fmtDT.format(d) + ' HKT' : '—'
}
/** Hour of day in HKT (0..23). */
export function hourHKT(ts: string | null | undefined): number {
  const d = toDate(ts)
  if (!d) return -1
  return (d.getUTCHours() + 8) % 24
}
/** Minutes of the HKT day, for plotting a timeline. */
export function minuteOfDayHKT(ts: string | null | undefined): number {
  const d = toDate(ts)
  if (!d) return -1
  return ((d.getUTCHours() + 8) % 24) * 60 + d.getUTCMinutes()
}
export function ageMin(ts: string | null | undefined, now = Date.now()): number | null {
  const d = toDate(ts)
  return d ? (now - d.getTime()) / 60000 : null
}
export function todayHKT(now = new Date()): string {
  return new Date(now.getTime() + 8 * 3600 * 1000).toISOString().slice(0, 10)
}
export function pct(x: number | null | undefined, digits = 0): string {
  return x == null || Number.isNaN(x) ? '—' : (x * 100).toFixed(digits) + ' %'
}
export function num(x: number | null | undefined, digits = 0): string {
  return x == null || Number.isNaN(x)
    ? '—'
    : x.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits })
}
export function signed(x: number | null | undefined, digits = 0): string {
  if (x == null || Number.isNaN(x)) return '—'
  return (x > 0 ? '+' : '') + x.toFixed(digits)
}
