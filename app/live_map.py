"""Live map: every aircraft within ~100 nm of HKIA with today's HKIA departures highlighted by P(delay > 15).

Data: a provider chain (all free, no key) — adsb.lol -> OpenSky anonymous bbox -> adsb.fi -> airplanes.live — tried in order until one
returns >= 1 aircraft (see PROVIDERS). Frames are cached process-wide for the provider's interval (10 s readsb family, 30 s OpenSky)
and the fragment re-runs at that interval so only the map refreshes. Callsign ↔ flight match: ICAO airline code + flight number
(callsign `CPA261` ↔ flight_no `CX 261`; the db's `airline` column is already ICAO, an IATA→ICAO map built from the db covers
callsigns that use the IATA prefix). Graceful fallback: last good frame + "feed unavailable" badge; never raises.
"""
from __future__ import annotations

import base64
import datetime as dt
import math
import re
import time

import numpy as np
import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

import data as D
import theme as T
from hkia import explain as E

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
MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
# Process-wide feed state (shared by every session so the anonymous OpenSky quota is spent once per server, not once per viewer).
_LAST_GOOD: dict = {"at": None, "data": None, "provider": None, "interval": 10}
_LAST_POLL: dict[str, float] = {}
_LAST_TRIED: list[str] = []

# A simple top-down airliner silhouette (white, nose up). mask=true lets deck.gl tint it with getColor.
_PLANE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><path fill="#fff" d="M32 2c2.4 0 4 3.6 4 8v14l24 14v6l-24-7v13'
    'l6 5v4l-10-3-10 3v-4l6-5V37L4 44v-6l24-14V10c0-4.4 1.6-8 4-8z"/></svg>')
PLANE_ICON = {"url": "data:image/svg+xml;base64," + base64.b64encode(_PLANE_SVG.encode()).decode(),
              "width": 64, "height": 64, "anchorX": 32, "anchorY": 32, "mask": True}

_CS_RE = re.compile(r"^([A-Z]{2,3})0*(\d{1,4})([A-Z]?)$")


# ------------------------------------------------------------------ feed
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


# ------------------------------------------------------------------ matching
def parse_callsign(cs: str) -> tuple[str, int, str] | None:
    m = _CS_RE.match((cs or "").replace(" ", "").upper())
    return (m.group(1), int(m.group(2)), m.group(3)) if m else None


@st.cache_data(ttl=D.TTL)
def iata_to_icao() -> dict[str, str]:
    """IATA prefix of flight_no -> most common ICAO `airline` in the db (e.g. CX -> CPA)."""
    df = D._q("SELECT flight_no, airline, COUNT(*) n FROM flights WHERE airline IS NOT NULL GROUP BY 1,2")
    if df.empty:
        return {}
    df["iata"] = df["flight_no"].str.split().str[0].str.upper()
    df = df.sort_values("n", ascending=False).drop_duplicates("iata")
    return dict(zip(df["iata"], df["airline"]))


def candidate_departures() -> pd.DataFrame:
    """Yesterday's + today's non-cancelled departures (HKT) with their latest prediction — the pool to match callsigns against."""
    today = D.now_hkt().date()
    frames = [D.departures(d.isoformat()) for d in (today - dt.timedelta(days=1), today)]
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True) if any(not f.empty for f in frames) else pd.DataFrame()
    if df.empty:
        return df
    df = df[df["status"] != "cancelled"].copy()
    m = iata_to_icao()
    num = df["flight_no"].str.extract(r"(\d+)")[0]
    df["_num"] = pd.to_numeric(num, errors="coerce")
    df["_icao"] = df["airline"].fillna(df["flight_no"].str.split().str[0].map(m)).str.upper()
    return df[df["_num"].notna()]


def match_departures(ac: pd.DataFrame, deps: pd.DataFrame) -> pd.DataFrame:
    """Left-join aircraft to our flights on (ICAO airline, flight number). Keeps only plausible departures:
    departed within the last 4 h, or still 'scheduled' (db lags the cron) but within 60 nm and ±a few hours of schedule."""
    ac = ac.copy()
    ac["matched"] = False
    for c in ("flight_no", "scheduled_ts", "destination", "sched_time", "actual_time", "p_delay15", "pred_delay_min", "delay_min", "status", "airline_name"):
        ac[c] = None
    if ac.empty or deps is None or deps.empty:
        return ac
    m = iata_to_icao()
    now = pd.Timestamp.now(tz="Asia/Hong_Kong")
    deps = deps.copy()
    deps["_act"] = pd.to_datetime(deps["actual_ts"], utc=True, errors="coerce").dt.tz_convert("Asia/Hong_Kong")
    idx: dict[tuple[str, int], list[int]] = {}
    for i, (ic, n) in enumerate(zip(deps["_icao"], deps["_num"])):
        idx.setdefault((ic, int(n)), []).append(i)
    for j, cs in enumerate(ac["callsign"]):
        p = parse_callsign(cs)
        if not p:
            continue
        prefix, num, _suffix = p
        icao = prefix if len(prefix) == 3 else m.get(prefix)
        rows = idx.get((icao, num)) if icao else None
        if not rows:
            continue
        best = None
        for i in rows:
            r = deps.iloc[i]
            if r["status"] == "departed":
                age = (now - r["_act"]).total_seconds() / 3600 if pd.notna(r["_act"]) else 99
                if 0 <= age <= 4 and (best is None or age < best[0]):
                    best = (age, i)
            elif r["status"] == "scheduled":
                # the db lags reality by up to ~30 min (cron), so a "scheduled" flight may already be airborne and climbing out
                near = bool(ac.at[j, "on_ground"]) or (pd.notna(ac.at[j, "dst_nm"]) and ac.at[j, "dst_nm"] < 60)
                lead_h = (r["sched_hkt"] - now).total_seconds() / 3600
                if near and -4 <= lead_h <= 2 and (best is None or abs(lead_h) < best[0]):
                    best = (abs(lead_h), i)
        if best is None:
            continue
        r = deps.iloc[best[1]]
        # scheduled_ts rides along so the "why" panel can look the flight up by its primary key: `match_departures`
        # already decided which day this callsign is, and flight numbers repeat across yesterday/today.
        ac.loc[j, ["matched", "flight_no", "scheduled_ts", "destination", "sched_time", "actual_time", "p_delay15",
                   "pred_delay_min", "delay_min", "status", "airline_name"]] = [
            True, r["flight_no"], r["scheduled_ts"], r["destination"], r["sched_time"], r["actual_time"],
            r["p_delay15"], r["pred_delay_min"], r["delay_min"], r["status"], r["airline_name"]]
    return ac


# ------------------------------------------------------------------ rendering
def _alt_grey(alt_ft: float, on_ground: bool) -> list[int]:
    """Other traffic: zinc-500 on the ground, zinc-400 -> zinc-100 by altitude."""
    if on_ground:
        return [113, 113, 122, 190]
    f = min(max(alt_ft, 0.0), 40000.0) / 40000.0
    lo, hi = (161, 161, 170), (244, 244, 245)
    return [round(lo[k] + (hi[k] - lo[k]) * f) for k in range(3)] + [235]


def _circle(lat: float, lon: float, nm: float, n: int = 120) -> list[list[float]]:
    r_km = nm * 1.852
    pts = []
    for k in range(n + 1):
        a = 2 * math.pi * k / n
        dlat = (r_km / 111.32) * math.cos(a)
        dlon = (r_km / (111.32 * math.cos(math.radians(lat)))) * math.sin(a)
        pts.append([lon + dlon, lat + dlat])
    return pts


def build_deck(ac: pd.DataFrame) -> pdk.Deck:
    rows = []
    for r in ac.itertuples(index=False):
        p = r.p_delay15
        tracked = bool(r.matched)
        if tracked and p is not None and not (isinstance(p, float) and np.isnan(p)):
            color, size = [*T.amber_rgb(float(p)), 255], 30
            p_txt = f"{float(p):.0%}"
        elif tracked:
            color, size, p_txt = [*T._hex_rgb(T.BLUE), 255], 28, "not scored"
            p = None
        else:
            color, size, p_txt = _alt_grey(float(r.alt_ft), bool(r.on_ground)), 17, ""
        pred = r.pred_delay_min
        rows.append({
            "lon": float(r.lon), "lat": float(r.lat), "angle": float(-r.track_deg), "color": color, "size": size, "icon": PLANE_ICON,
            "callsign": r.callsign or "—", "reg": r.r if isinstance(r.r, str) else "", "type": r.t if isinstance(r.t, str) else "",
            "alt": "ground" if r.on_ground else f"{int(r.alt_ft):,} ft", "spd": "" if pd.isna(r.gs_kt) else f"{r.gs_kt:.0f} kt",
            "tracked": tracked, "flight_no": r.flight_no or "", "dest": r.destination or "", "sched": r.sched_time or "",
            "actual": r.actual_time or "—", "p": p_txt, "pred": "" if pred is None or pd.isna(pred) else f"{float(pred):.0f} min",
            "line2": (f"{r.flight_no} → {r.destination} · {r.airline_name}<br/>sched {r.sched_time} · actual {r.actual_time or '—'}"
                      f"<br/>P(delay > 15) {p_txt}" + (f" · pred {float(pred):.0f} min" if pred is not None and not pd.isna(pred) else "")
                      if tracked else "not an HKIA departure we track"),
        })
    others = [d for d in rows if not d["tracked"]]
    tracked = [d for d in rows if d["tracked"]]
    ring = [*T._hex_rgb(T.BORDER_2), 160]
    accent = T._hex_rgb(T.ACCENT)
    layers = [
        pdk.Layer("PolygonLayer", data=[{"poly": _circle(HKIA_LAT, HKIA_LON, RADIUS_NM)}, {"poly": _circle(HKIA_LAT, HKIA_LON, 50)}],
                  get_polygon="poly", stroked=True, filled=False, get_line_color=ring, line_width_min_pixels=1, pickable=False),
        pdk.Layer("ScatterplotLayer", data=[{"lon": HKIA_LON, "lat": HKIA_LAT}], get_position="[lon, lat]", get_radius=900,
                  get_fill_color=[*accent, 70], get_line_color=[*accent, 230], stroked=True, line_width_min_pixels=1.5, pickable=False),
        pdk.Layer("TextLayer", data=[{"lon": HKIA_LON, "lat": HKIA_LAT - 0.035, "txt": "VHHH · HKIA"}], get_position="[lon, lat]",
                  get_text="txt", get_color=[*T._hex_rgb(T.INK_2), 255], get_size=12, get_alignment_baseline="'top'", pickable=False,
                  font_family="Menlo, Consolas, monospace"),
        pdk.Layer("IconLayer", data=others, get_position="[lon, lat]", get_icon="icon", get_angle="angle", get_color="color",
                  get_size="size", size_units="pixels", size_min_pixels=10, size_max_pixels=22, pickable=True, billboard=False,
                  auto_highlight=True, highlight_color=[*accent, 255]),
        pdk.Layer("IconLayer", data=tracked, get_position="[lon, lat]", get_icon="icon", get_angle="angle", get_color="color",
                  get_size="size", size_units="pixels", size_min_pixels=18, size_max_pixels=36, pickable=True, billboard=False,
                  auto_highlight=True, highlight_color=[250, 250, 250, 255]),
    ]
    tooltip = {
        "html": "<div style='font-family:Menlo,Consolas,monospace;font-size:12px;line-height:1.5'><b>{callsign}</b> {reg} {type}<br/>{alt} · {spd}<br/>{line2}</div>",
        "style": {"backgroundColor": T.SURFACE_3, "color": T.INK, "border": f"1px solid {T.BORDER_2}", "borderRadius": "8px", "padding": "8px 10px"},
    }
    view = pdk.ViewState(latitude=HKIA_LAT + 0.05, longitude=HKIA_LON, zoom=7.6, pitch=0, bearing=0)
    return pdk.Deck(layers=layers, initial_view_state=view, map_style=MAP_STYLE, tooltip=tooltip)


def _legend_html() -> str:
    ramp = ", ".join(T.AMBER_RAMP)
    return (
        '<div class="hk-legend">'
        f'<span><span class="sw" style="background:linear-gradient(90deg,{ramp})"></span>HKIA departure · P(delay > 15) 0 → 100 %</span>'
        f'<span><span class="dot" style="background:{T.BLUE}"></span>tracked, not scored</span>'
        f'<span><span class="sw" style="background:linear-gradient(90deg,#a1a1aa,#f4f4f5)"></span>other traffic · altitude low → high</span>'
        f'<span class="muted">rings 50 / 100 nm · basemap CARTO</span></div>')


def render() -> None:
    """Fragment wrapper: the refresh interval follows the provider that served the last frame (10 s readsb family, 30 s OpenSky)."""
    st.fragment(_render, run_every=f"{_LAST_GOOD['interval']}s")()


def _render() -> None:
    ac, err, fetched_at = fetch_adsb()
    deps = candidate_departures()
    n_ac = 0 if ac is None else len(ac)
    matched = match_departures(ac, deps) if ac is not None else None
    n_tr = 0 if matched is None else int(matched["matched"].sum())

    col_map, col_side = st.columns([3, 1.15], gap="medium")
    with col_map:
        age = f"{max(0, time.time() - fetched_at):.0f} s ago" if fetched_at else "—"
        prov = _LAST_GOOD["provider"] or "—"
        items = [T.badge(f"<b>{n_ac}</b> aircraft in {RADIUS_NM} nm"), T.badge(f"<b>{n_tr}</b> HKIA departures tracked", "accent" if n_tr else "")]
        if err:
            items.append(T.badge(f"{err} — showing last good frame" if ac is not None else "feed unavailable", "warn" if ac is not None else "crit"))
        items.append(T.badge(f"{prov} · {age} · every {_LAST_GOOD['interval']} s"))
        T.badges(*items)
        if ac is None:
            st.warning(f"ADS-B feed unavailable ({err}); no cached frame yet. The map retries every {_LAST_GOOD['interval']} s.")
        else:
            st.pydeck_chart(build_deck(matched), height=600, use_container_width=True)
        st.markdown(_legend_html(), unsafe_allow_html=True)
    with col_side:
        m1, m2 = st.columns(2)
        m1.metric("In range", f"{n_ac}", f"within {RADIUS_NM} nm", delta_color="off")
        m2.metric("Tracked", f"{n_tr}", "HKIA departures", delta_color="off")
        wx = D.weather_now()
        mt = wx["metar"]
        if mt:
            T.strip(mt["raw_ob"])
        tc = wx["tc_active"]
        warn = [w for w in wx["warnings"] if w["code"] != "WTCSGNL"] if tc else wx["warnings"]
        wb = []
        if tc:
            wb.append(T.badge(f"TC signal {tc[0]['signal']} {tc[0].get('tc_name') or ''}", "crit"))
        wb += [T.badge(w["name"], "warn") for w in warn]
        if not wb:
            wb.append(T.badge("HKO: no warnings in force", "ok"))
        T.badges(*wb)
        st.markdown("#### Tracked departures")
        if matched is not None and n_tr:
            t = matched[matched["matched"]].sort_values("sched_time").reset_index(drop=True)
            tbl = pd.DataFrame({"Sched": t["sched_time"], "Flight": t["flight_no"], "To": t["destination"],
                                "P(delay>15)": pd.to_numeric(t["p_delay15"], errors="coerce")})
            event = st.dataframe(tbl, hide_index=True, width="stretch", height=min(420, 38 + 35 * len(tbl)),
                                 key="tracked_departures", on_select="rerun", selection_mode="single-row",
                                 column_config={"P(delay>15)": st.column_config.ProgressColumn("P(>15)", min_value=0, max_value=1, format="%.2f")})
            _why_panel(t, event)
        else:
            st.caption("No tracked departure inside the 100 nm ring right now — they leave it ~15 min after take-off.")
        st.caption("Match = ICAO airline code + flight number (CPA261 ↔ CX 261); colour = that flight's latest P(delay > 15).")


def _why_panel(t: pd.DataFrame, event) -> None:
    """Top-3 drivers of the selected tracked flight's latest score. `t` is the tracked frame, which carries the
    matched flight's own `scheduled_ts` — the panel must not re-resolve by flight number, because the candidate pool
    spans yesterday + today and ~400 numbers appear on both days."""
    st.markdown("#### Why this prediction")
    # the frame is rebuilt from a live ADS-B frame every 10 s, so a stored row index can outlive the row it named
    picked = [i for i in (getattr(getattr(event, "selection", None), "rows", []) or []) if 0 <= i < len(t)]
    if not picked:
        st.caption("Select a tracked departure above to see the three features that moved its P(delay > 15) the most.")
        return
    r = t.iloc[picked[0]]
    sched = str(r["scheduled_ts"])
    date = sched[:10]                            # flights.date == the HKT calendar day of the scheduled departure
    rows = D.explanations(date).get((r["flight_no"], sched), [])
    st.caption(f"**{r['flight_no']}** → {r['destination']} · scheduled {r['sched_time']} HKT")
    T.why_lines(rows, empty="No attribution stored for this flight — they are kept for flights that have not departed yet.")
    if rows:
        st.caption(E.FOOTER)
