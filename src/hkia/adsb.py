"""Shared ADS-B feed: provider chain, normalisers, callsign parsing. No database, no Streamlit.

Extracted from `app/live_map.py` (2026-08-20) so the dashboard and the ingestion cron read the same feed the same way —
`app.live_map` re-exports every name below, and `hkia.ingest_adsb` snapshots the frames into SQLite.

Providers (all free, no key) are tried in order until one returns >= 1 aircraft; frames are cached process-wide for the
serving provider's interval (10 s readsb family, 30 s OpenSky anonymous). `fetch_adsb` never raises: on total failure it
returns the last good frame with an error string.

Registration: the readsb-family feeds carry `r` (registration) and `t` (type). OpenSky's /states/all does NOT — it gives
only `icao24` (the `hex`), so frames served by OpenSky have `r is None`. Mapping hex -> registration needs an external
table (e.g. the OpenSky aircraft database CSV); not built. `hex` alone is a stable aircraft identity, which is all the
rotation linkage in `hkia.rotations` needs.
"""
from __future__ import annotations

import math
import re
import time

import numpy as np
import pandas as pd
import requests

HKIA_LAT, HKIA_LON, RADIUS_NM = 22.308, 113.918, 100
UA = {"User-Agent": "hkia-delay-predictor (github.com/dsjwong/hkia-delay-predictor)"}
# Provider chain, tried in order until one yields >= 1 aircraft. Streamlit Cloud's egress IP gets an empty `ac` list from adsb.lol
# (home IPs get ~50), so OpenSky's anonymous bbox endpoint is the usual fallback there. (name, url, format, min poll seconds)
PROVIDERS: list[tuple[str, str, str, int]] = [
    ("adsb.lol", f"https://api.adsb.lol/v2/lat/{HKIA_LAT}/lon/{HKIA_LON}/dist/{RADIUS_NM}", "readsb", 10),
    ("OpenSky", "https://opensky-network.org/api/states/all?lamin=20.6&lomin=112.1&lamax=24.0&lomax=115.7", "opensky", 30),
    ("adsb.fi", f"https://opendata.adsb.fi/api/v2/lat/{HKIA_LAT}/lon/{HKIA_LON}/dist/{RADIUS_NM}", "readsb", 10),
    ("airplanes.live", f"https://api.airplanes.live/v2/point/{HKIA_LAT}/{HKIA_LON}/{RADIUS_NM}", "readsb", 10),
]
ADSB_URL = PROVIDERS[0][1]  # back-compat
COLS = ["hex", "callsign", "lat", "lon", "alt_ft", "on_ground", "gs_kt", "track_deg", "t", "r", "dst_nm"]
# Process-wide feed state (shared by every session so the anonymous OpenSky quota is spent once per server, not once per viewer).
_LAST_GOOD: dict = {"at": None, "data": None, "provider": None, "interval": 10}
_LAST_POLL: dict[str, float] = {}
_LAST_TRIED: list[str] = []

_CS_RE = re.compile(r"^([A-Z]{2,3})0*(\d{1,4})([A-Z]?)$")


def dist_nm(lat, lon) -> np.ndarray:
    """Great-circle distance from HKIA in nautical miles (vectorised)."""
    la1, lo1 = math.radians(HKIA_LAT), math.radians(HKIA_LON)
    la2, lo2 = np.radians(np.asarray(lat, dtype=float)), np.radians(np.asarray(lon, dtype=float))
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * 3440.065 * np.arcsin(np.sqrt(a))


def normalise_readsb(js: dict) -> pd.DataFrame:
    """adsb.lol / adsb.fi / airplanes.live (readsb JSON: hex, flight, lat, lon, alt_baro, gs, track, t, r, dst) -> standard frame."""
    ac = pd.DataFrame(js.get("ac") or [])
    for c in ("hex", "flight", "lat", "lon", "alt_baro", "gs", "track", "t", "r", "dst"):
        if c not in ac.columns:
            ac[c] = np.nan
    ac = ac[ac["lat"].notna() & ac["lon"].notna()].copy()
    ac["callsign"] = ac["flight"].fillna("").astype(str).str.strip().str.upper()
    ac["on_ground"] = ac["alt_baro"].astype(str).str.lower().eq("ground")
    ac["alt_ft"] = pd.to_numeric(ac["alt_baro"], errors="coerce").fillna(0).clip(lower=0)
    ac["gs_kt"] = pd.to_numeric(ac["gs"], errors="coerce")
    ac["track_deg"] = pd.to_numeric(ac["track"], errors="coerce").fillna(0)
    ac["dst_nm"] = pd.to_numeric(ac["dst"], errors="coerce")
    miss = ac["dst_nm"].isna()
    if miss.any():
        ac.loc[miss, "dst_nm"] = dist_nm(ac.loc[miss, "lat"], ac.loc[miss, "lon"])
    return ac[COLS].reset_index(drop=True)


def normalise_opensky(js: dict) -> pd.DataFrame:
    """OpenSky /states/all -> standard frame. State vector indices: 0 icao24, 1 callsign, 5 lon, 6 lat, 7 baro alt (m), 8 on_ground,
    9 velocity (m/s), 10 true_track, 13 geo alt (m). Filtered to <= RADIUS_NM of HKIA."""
    rows = []
    for s in js.get("states") or []:
        if s is None or len(s) < 11 or s[5] is None or s[6] is None:
            continue
        alt_m = s[7] if s[7] is not None else (s[13] if len(s) > 13 else None)
        rows.append({"hex": s[0], "callsign": (s[1] or "").strip().upper(), "lat": float(s[6]), "lon": float(s[5]),
                     "alt_ft": max(0.0, float(alt_m) * 3.28084) if alt_m is not None else 0.0, "on_ground": bool(s[8]),
                     "gs_kt": float(s[9]) * 1.943844 if s[9] is not None else np.nan,
                     "track_deg": float(s[10]) if s[10] is not None else 0.0, "t": None, "r": None})
    ac = pd.DataFrame(rows, columns=COLS[:-1])
    ac["dst_nm"] = dist_nm(ac["lat"], ac["lon"]) if len(ac) else pd.Series(dtype=float)
    return ac[ac["dst_nm"] <= RADIUS_NM][COLS].reset_index(drop=True)


def _get(url: str) -> dict:
    r = requests.get(url, timeout=8, headers=UA)
    r.raise_for_status()
    return r.json()


def fetch_chain(now: float | None = None) -> tuple[pd.DataFrame | None, str | None, list[str]]:
    """Try each provider in order; first one with >= 1 aircraft wins. Returns (frame, provider, providers tried).
    Providers are not polled faster than their min interval (OpenSky anonymous quota)."""
    now = time.time() if now is None else now
    tried: list[str] = []
    for name, url, fmt, min_s in PROVIDERS:
        if now - _LAST_POLL.get(name, 0.0) < min_s:
            continue
        tried.append(name)
        _LAST_POLL[name] = now
        try:
            js = _get(url)
            ac = normalise_opensky(js) if fmt == "opensky" else normalise_readsb(js)
        except Exception:  # noqa: BLE001 — next provider
            continue
        if len(ac):
            return ac, name, tried
    return None, None, tried


def fetch_adsb(now: float | None = None) -> tuple[pd.DataFrame | None, str | None, float]:
    """(aircraft frame, error, fetched_at). Serves the last good frame while it is younger than the active provider's interval,
    otherwise runs the chain; on total failure keeps the last good frame and reports which providers were tried. Never raises."""
    now = time.time() if now is None else now
    if _LAST_GOOD["data"] is not None and now - (_LAST_GOOD["at"] or 0) < _LAST_GOOD["interval"]:
        return _LAST_GOOD["data"], None, _LAST_GOOD["at"]
    try:
        ac, prov, tried = fetch_chain(now)
    except Exception as e:  # noqa: BLE001
        ac, prov, tried = None, None, [f"{type(e).__name__}"]
    _LAST_TRIED[:] = tried
    if ac is not None:
        _LAST_GOOD.update(at=now, data=ac, provider=prov, interval=next(p[3] for p in PROVIDERS if p[0] == prov))
        return ac, None, now
    return _LAST_GOOD["data"], "feed degraded: " + (", ".join(tried) if tried else "rate-limited, retrying"), _LAST_GOOD["at"] or 0.0


def parse_callsign(cs: str) -> tuple[str, int, str] | None:
    """`CPA0261A` -> ("CPA", 261, "A"). Returns None for anything that is not <2-3 letters><digits><optional letter>."""
    m = _CS_RE.match((cs or "").replace(" ", "").upper())
    return (m.group(1), int(m.group(2)), m.group(3)) if m else None
