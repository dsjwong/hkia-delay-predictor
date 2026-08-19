import { describe, expect, it } from 'vitest'
import { buildIndex, flightIata, flightNumber, matchFlight, parseCallsign } from './callsign'
import type { Flight } from './types'

const NOW = Date.parse('2026-08-19T10:00:00Z') // 18:00 HKT
const f = (over: Partial<Flight>): Flight => ({
  flight_no: 'CX 261',
  airline: 'CPA',
  dest: 'CDG',
  sched_ts: '2026-08-19T09:30:00Z',
  est_ts: null,
  actual_ts: '2026-08-19T09:45:00Z',
  status: 'departed',
  terminal: 'T1',
  gate: '1',
  codeshares: null,
  delay_min: 15,
  p: 0.3,
  pred_min: 12,
  scored_at: '2026-08-19T09:00:00Z',
  ...over,
})
const I2I = { CX: 'CPA', UO: 'HKE', HX: 'CRK' }

describe('parseCallsign', () => {
  it('parses ICAO + number + optional suffix, strips zeros/spaces', () => {
    expect(parseCallsign('CPA261')).toEqual({ prefix: 'CPA', num: 261, suffix: '' })
    expect(parseCallsign('HKE 0123A ')).toEqual({ prefix: 'HKE', num: 123, suffix: 'A' })
    expect(parseCallsign('cx261')).toEqual({ prefix: 'CX', num: 261, suffix: '' })
    expect(parseCallsign('B-LRA')).toBeNull()
    expect(parseCallsign('')).toBeNull()
  })
  it('flight number helpers', () => {
    expect(flightNumber('CX 261')).toBe(261)
    expect(flightIata('5J 111')).toBe('5J')
  })
})

describe('matchFlight', () => {
  const pool = [
    f({}),
    f({ flight_no: 'CX 261', sched_ts: '2026-08-18T09:30:00Z', actual_ts: '2026-08-18T09:40:00Z' }), // yesterday's leg, too old
    f({
      flight_no: 'UO 700',
      airline: 'HKE',
      status: 'scheduled',
      actual_ts: null,
      sched_ts: '2026-08-19T10:20:00Z',
      p: null,
    }),
    f({ flight_no: 'HX 1', airline: 'CRK', status: 'cancelled', actual_ts: null }),
  ]
  const idx = buildIndex(pool, I2I)
  it('matches ICAO callsign to the departure that left within 4 h', () => {
    const m = matchFlight({ callsign: 'CPA261', onGround: false, distNm: 80 }, idx, I2I, NOW)
    expect(m?.actual_ts).toBe('2026-08-19T09:45:00Z')
  })
  it('maps an IATA-prefixed callsign through the IATA->ICAO table', () => {
    expect(matchFlight({ callsign: 'CX261', onGround: false, distNm: 80 }, idx, I2I, NOW)?.flight_no).toBe('CX 261')
  })
  it('matches a still-"scheduled" flight only when near the airport and close to schedule', () => {
    expect(matchFlight({ callsign: 'HKE700', onGround: true, distNm: 0 }, idx, I2I, NOW)?.flight_no).toBe('UO 700')
    expect(matchFlight({ callsign: 'HKE700', onGround: false, distNm: 90 }, idx, I2I, NOW)).toBeNull()
  })
  it('ignores cancelled flights and unknown callsigns', () => {
    expect(matchFlight({ callsign: 'CRK1', onGround: true, distNm: 0 }, idx, I2I, NOW)).toBeNull()
    expect(matchFlight({ callsign: 'SIA1', onGround: false, distNm: 10 }, idx, I2I, NOW)).toBeNull()
  })
})
