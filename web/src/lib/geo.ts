/** Dead-reckoning + small geo helpers for the live map. */
export const NM_KM = 1.852
export const HKIA = { lat: 22.308, lon: 113.918 }

export interface Track {
  lat: number
  lon: number
  gsKt: number | null
  trackDeg: number | null
  /** ms epoch of the observation the position refers to */
  t: number
}

/** Position `dtSec` seconds after the observation, along `trackDeg` at `gsKt` (flat-earth, fine for < 1 min). */
export function deadReckon(tr: Track, dtSec: number, maxSec = 30): { lat: number; lon: number } {
  const dt = Math.min(Math.max(dtSec, 0), maxSec)
  if (!tr.gsKt || tr.trackDeg == null || dt <= 0) return { lat: tr.lat, lon: tr.lon }
  const dKm = (tr.gsKt * NM_KM * dt) / 3600
  const th = (tr.trackDeg * Math.PI) / 180
  const dlat = (dKm / 111.32) * Math.cos(th)
  const dlon = (dKm / (111.32 * Math.cos((tr.lat * Math.PI) / 180))) * Math.sin(th)
  return { lat: tr.lat + dlat, lon: tr.lon + dlon }
}

export function haversineNm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371.0088
  const toR = Math.PI / 180
  const dLat = (lat2 - lat1) * toR
  const dLon = (lon2 - lon1) * toR
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * toR) * Math.cos(lat2 * toR) * Math.sin(dLon / 2) ** 2
  return (2 * R * Math.asin(Math.sqrt(a))) / NM_KM
}

/** Closed ring of [lon, lat] points `nm` nautical miles around a centre. */
export function circle(lat: number, lon: number, nm: number, n = 120): [number, number][] {
  const rKm = nm * NM_KM
  const pts: [number, number][] = []
  for (let k = 0; k <= n; k++) {
    const a = (2 * Math.PI * k) / n
    const dlat = (rKm / 111.32) * Math.cos(a)
    const dlon = (rKm / (111.32 * Math.cos((lat * Math.PI) / 180))) * Math.sin(a)
    pts.push([lon + dlon, lat + dlat])
  }
  return pts
}
