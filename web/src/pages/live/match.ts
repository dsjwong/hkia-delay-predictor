import type { Aircraft } from '@/lib/adsb'
import { buildIndex, matchFlight } from '@/lib/callsign'
import { airlineName, destLabel } from '@/lib/data'
import type { Flight, Meta } from '@/lib/types'

export interface TrackedAircraft extends Aircraft {
  flight: Flight | null
  airlineName: string
  destLabel: string
}

export function trackAircraft(aircraft: Aircraft[], pool: Flight[], meta: Meta | null, now = Date.now()): TrackedAircraft[] {
  const i2i = meta?.iata_to_icao ?? {}
  const idx = buildIndex(pool, i2i)
  return aircraft.map((a) => {
    const f = matchFlight({ callsign: a.callsign, onGround: a.onGround, distNm: a.distNm }, idx, i2i, now)
    return { ...a, flight: f, airlineName: f ? airlineName(meta, f.airline) : '', destLabel: f ? destLabel(meta, f.dest) : '' }
  })
}
