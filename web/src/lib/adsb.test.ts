import { describe, expect, it, vi } from 'vitest'
import { fetchAircraft, normalise } from './adsb'

const sample = {
  now: 1,
  ac: [
    {
      hex: '781da2',
      flight: 'HXA4095 ',
      r: 'B-329F',
      t: 'A20N',
      alt_baro: 27450,
      gs: 471.1,
      track: 238.8,
      lat: 22.9,
      lon: 113.2,
      dst: 50.2,
      seen_pos: 1.5,
    },
    { hex: '780abc', flight: 'CPA261', alt_baro: 'ground', gs: 12, track: 70, lat: 22.31, lon: 113.92 },
    { hex: 'nolatlon', flight: 'XXX1' },
  ],
}

describe('normalise', () => {
  it('keeps aircraft with a position, trims callsigns, flags ground, computes distance when missing', () => {
    const ac = normalise(sample, 100000)
    expect(ac.map((a) => a.hex)).toEqual(['781da2', '780abc'])
    expect(ac[0].callsign).toBe('HXA4095')
    expect(ac[0].posAt).toBe(98500)
    expect(ac[1].onGround).toBe(true)
    expect(ac[1].altFt).toBe(0)
    expect(ac[1].distNm).toBeLessThan(1)
  })
})

describe('fetchAircraft', () => {
  it('falls through to the next route when the first fails, and reports the route used', async () => {
    const calls: string[] = []
    const fetcher = vi.fn(async (url: string | URL | Request) => {
      const u = String(url)
      calls.push(u)
      if (u.startsWith('https://api.adsb.lol')) throw new TypeError('Failed to fetch')
      return new Response(JSON.stringify(sample), { status: 200, headers: { 'content-type': 'application/json' } })
    }) as unknown as typeof fetch
    const r = await fetchAircraft(fetcher)
    expect(r.route).toBe('proxy')
    expect(r.aircraft.length).toBe(2)
    expect(calls[0]).toContain('api.adsb.lol')
    expect(calls[1]).toContain('cors.lol')
    // sticky: the next call starts with the proxy
    calls.length = 0
    await fetchAircraft(fetcher)
    expect(calls[0]).toContain('cors.lol')
  })
  it('throws when every route fails', async () => {
    const fetcher = vi.fn(async () => new Response('nope', { status: 500 })) as unknown as typeof fetch
    await expect(fetchAircraft(fetcher)).rejects.toThrow(/HTTP 500/)
  })
})
