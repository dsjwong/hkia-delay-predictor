import { describe, expect, it, vi } from 'vitest'
import { airlineName, dataBases, destLabel, fetchJson } from './data'
import type { Meta } from './types'

describe('fetchJson', () => {
  it('loads from the first working base and reports it', async () => {
    const fetcher = vi.fn(async (url: string | URL | Request) => {
      const u = String(url)
      expect(u).toMatch(/meta\.json\?v=\d+$/)
      return new Response(JSON.stringify({ ok: true }), { status: 200 })
    }) as unknown as typeof fetch
    const r = await fetchJson<{ ok: boolean }>('meta.json', fetcher)
    expect(r.data.ok).toBe(true)
    expect(dataBases()).toContain(r.source)
  })
  it('throws with the last error when every base fails', async () => {
    const fetcher = vi.fn(async () => new Response('', { status: 404 })) as unknown as typeof fetch
    await expect(fetchJson('nope.json', fetcher)).rejects.toThrow(/HTTP 404/)
  })
})

describe('labels', () => {
  const meta = { airlines: { CPA: 'Cathay Pacific' }, airports: { CDG: { city: 'Paris CDG', country: 'France' }, XYZ: { city: 'XYZ', country: '' } } } as unknown as Meta
  it('fall back to the code when unknown', () => {
    expect(airlineName(meta, 'CPA')).toBe('Cathay Pacific')
    expect(airlineName(meta, 'ZZZ')).toBe('ZZZ')
    expect(airlineName(null, null)).toBe('?')
    expect(destLabel(meta, 'CDG')).toBe('Paris CDG (CDG)')
    expect(destLabel(meta, 'XYZ')).toBe('XYZ')
  })
})
