/** Callsign <-> HKIA departure matching (port of app/live_map.py): ICAO airline code + flight number, e.g. CPA261 <-> "CX 261". */
import type { Flight } from './types'

const CS_RE = /^([A-Z]{2,3})0*(\d{1,4})([A-Z]?)$/

export interface ParsedCallsign {
  prefix: string
  num: number
  suffix: string
}

export function parseCallsign(cs: string | null | undefined): ParsedCallsign | null {
  const m = CS_RE.exec((cs ?? '').replace(/\s+/g, '').toUpperCase())
  return m ? { prefix: m[1], num: parseInt(m[2], 10), suffix: m[3] } : null
}

export function flightNumber(flightNo: string): number | null {
  const m = /(\d+)/.exec(flightNo)
  return m ? parseInt(m[1], 10) : null
}

export function flightIata(flightNo: string): string {
  return flightNo.trim().split(/\s+/)[0].toUpperCase()
}

/** Candidate pool: yesterday + today, non-cancelled, keyed by "ICAO|number". */
export function buildIndex(flights: Flight[], iataToIcao: Record<string, string>): Map<string, Flight[]> {
  const idx = new Map<string, Flight[]>()
  for (const f of flights) {
    if (f.status === 'cancelled') continue
    const num = flightNumber(f.flight_no)
    const icao = (f.airline ?? iataToIcao[flightIata(f.flight_no)] ?? '').toUpperCase()
    if (num == null || !icao) continue
    const k = `${icao}|${num}`
    const arr = idx.get(k)
    if (arr) arr.push(f)
    else idx.set(k, [f])
  }
  return idx
}

export interface MatchInput {
  callsign: string | null | undefined
  onGround: boolean
  distNm: number | null
}

/** Pick the departure this aircraft most plausibly is:
 *  - departed within the last 4 h (closest), or
 *  - still "scheduled" in the db (cron lag) but near the airport (on ground / < 60 nm) and within -4 h..+2 h of schedule. */
export function matchFlight(
  ac: MatchInput,
  idx: Map<string, Flight[]>,
  iataToIcao: Record<string, string>,
  now = Date.now(),
): Flight | null {
  const p = parseCallsign(ac.callsign)
  if (!p) return null
  const icao = p.prefix.length === 3 ? p.prefix : iataToIcao[p.prefix]
  if (!icao) return null
  const rows = idx.get(`${icao}|${p.num}`)
  if (!rows) return null
  let best: { score: number; f: Flight } | null = null
  for (const f of rows) {
    if (f.status === 'departed') {
      const act = f.actual_ts ? Date.parse(f.actual_ts) : NaN
      const ageH = Number.isNaN(act) ? 99 : (now - act) / 3.6e6
      if (ageH >= 0 && ageH <= 4 && (!best || ageH < best.score)) best = { score: ageH, f }
    } else if (f.status === 'scheduled') {
      const near = ac.onGround || (ac.distNm != null && ac.distNm < 60)
      const leadH = (Date.parse(f.sched_ts) - now) / 3.6e6
      if (near && leadH >= -4 && leadH <= 2 && (!best || Math.abs(leadH) < best.score))
        best = { score: Math.abs(leadH), f }
    }
  }
  return best?.f ?? null
}
