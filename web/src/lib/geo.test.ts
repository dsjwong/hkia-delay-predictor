import { describe, expect, it } from 'vitest'
import { circle, deadReckon, haversineNm } from './geo'

describe('deadReckon', () => {
  const tr = { lat: 22.308, lon: 113.918, gsKt: 360, trackDeg: 90, t: 0 }
  it('moves east at 360 kt: 1 nm in 10 s', () => {
    const p = deadReckon(tr, 10)
    expect(p.lat).toBeCloseTo(22.308, 6)
    expect(haversineNm(tr.lat, tr.lon, p.lat, p.lon)).toBeCloseTo(1, 2)
  })
  it('moves north along track 0 and caps extrapolation at maxSec', () => {
    const p = deadReckon({ ...tr, trackDeg: 0 }, 120, 30)
    expect(p.lon).toBeCloseTo(tr.lon, 6)
    expect(haversineNm(tr.lat, tr.lon, p.lat, p.lon)).toBeCloseTo(3, 2)
  })
  it('stays put without speed/track or for negative dt', () => {
    expect(deadReckon({ ...tr, gsKt: null }, 10)).toEqual({ lat: tr.lat, lon: tr.lon })
    expect(deadReckon(tr, -5)).toEqual({ lat: tr.lat, lon: tr.lon })
  })
})

describe('circle', () => {
  it('is a closed ring of points ~r nm from the centre', () => {
    const ring = circle(22.308, 113.918, 100, 36)
    expect(ring.length).toBe(37)
    expect(ring[0]).toEqual(ring[36])
    for (const [lon, lat] of ring) expect(haversineNm(22.308, 113.918, lat, lon)).toBeCloseTo(100, 0)
  })
})
