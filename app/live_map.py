"""Live map: every aircraft within ~100 nm of HKIA (adsb.lol, free, no key) with today's HKIA departures highlighted by P(delay > 15).

Data: https://api.adsb.lol/v2/lat/22.308/lon/113.918/dist/100  (fields hex, flight=callsign, lat, lon, alt_baro, gs, track, t, r).
Cached 10 s; the fragment re-runs every 10 s so only the map refreshes. Callsign ↔ flight match: ICAO airline code + flight number
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

HKIA_LAT, HKIA_LON, RADIUS_NM = 22.308, 113.918, 100
ADSB_URL = f"https://api.adsb.lol/v2/lat/{HKIA_LAT}/lon/{HKIA_LON}/dist/{RADIUS_NM}"
MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
_LAST_GOOD: dict = {"at": None, "data": None}

# A simple top-down airliner silhouette (white, nose up). mask=true lets deck.gl tint it with getColor.
_PLANE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><path fill="#fff" d="M32 2c2.4 0 4 3.6 4 8v14l24 14v6l-24-7v13'
    'l6 5v4l-10-3-10 3v-4l6-5V37L4 44v-6l24-14V10c0-4.4 1.6-8 4-8z"/></svg>')
PLANE_ICON = {"url": "data:image/svg+xml;base64," + base64.b64encode(_PLANE_SVG.encode()).decode(),
              "width": 64, "height": 64, "anchorX": 32, "anchorY": 32, "mask": True}

_CS_RE = re.compile(r"^([A-Z]{2,3})0*(\d{1,4})([A-Z]?)$")


# ------------------------------------------------------------------ feed
def _fetch_raw() -> dict:
    r = requests.get(ADSB_URL, timeout=8, headers={"User-Agent": "hkia-delay-predictor (github.com/dsjwong/hkia-delay-predictor)"})
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=10, show_spinner=False)
def fetch_adsb(_bucket: int) -> tuple[pd.DataFrame | None, str | None, float]:
    """(aircraft frame, error, fetched_at). `_bucket` just busts the cache every 10 s."""
    try:
        js = _fetch_raw()
        ac = pd.DataFrame(js.get("ac", []))
        if ac.empty:
            ac = pd.DataFrame(columns=["hex", "flight", "lat", "lon", "alt_baro", "gs", "track", "t", "r"])
        for c in ("flight", "lat", "lon", "alt_baro", "gs", "track", "t", "r", "dst"):
            if c not in ac.columns:
                ac[c] = np.nan
        ac = ac[ac["lat"].notna() & ac["lon"].notna()].copy()
        ac["callsign"] = ac["flight"].fillna("").astype(str).str.strip().str.upper()
        ac["on_ground"] = ac["alt_baro"].astype(str).str.lower().eq("ground")
        ac["alt_ft"] = pd.to_numeric(ac["alt_baro"], errors="coerce").fillna(0).clip(lower=0)
        ac["gs_kt"] = pd.to_numeric(ac["gs"], errors="coerce")
        ac["track_deg"] = pd.to_numeric(ac["track"], errors="coerce").fillna(0)
        ac["dst_nm"] = pd.to_numeric(ac["dst"], errors="coerce")
        out = ac[["hex", "callsign", "lat", "lon", "alt_ft", "on_ground", "gs_kt", "track_deg", "t", "r", "dst_nm"]].reset_index(drop=True)
        _LAST_GOOD.update(at=time.time(), data=out)
        return out, None, _LAST_GOOD["at"]
    except Exception as e:  # noqa: BLE001 — never crash the page
        return _LAST_GOOD["data"], f"{type(e).__name__}: {str(e)[:80]}", _LAST_GOOD["at"] or 0.0


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
    for c in ("flight_no", "destination", "sched_time", "actual_time", "p_delay15", "pred_delay_min", "delay_min", "status", "airline_name"):
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
        ac.loc[j, ["matched", "flight_no", "destination", "sched_time", "actual_time", "p_delay15", "pred_delay_min", "delay_min",
                   "status", "airline_name"]] = [True, r["flight_no"], r["destination"], r["sched_time"], r["actual_time"],
                                                 r["p_delay15"], r["pred_delay_min"], r["delay_min"], r["status"], r["airline_name"]]
    return ac


# ------------------------------------------------------------------ rendering
def _alt_grey(alt_ft: float, on_ground: bool) -> list[int]:
    if on_ground:
        return [95, 104, 122, 200]
    f = min(max(alt_ft, 0.0), 40000.0) / 40000.0
    lo, hi = (120, 130, 150), (236, 240, 246)
    return [round(lo[k] + (hi[k] - lo[k]) * f) for k in range(3)] + [230]


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
            color, size, p_txt = [57, 135, 229, 255], 28, "not scored"
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
    layers = [
        pdk.Layer("PolygonLayer", data=[{"poly": _circle(HKIA_LAT, HKIA_LON, RADIUS_NM)}, {"poly": _circle(HKIA_LAT, HKIA_LON, 50)}],
                  get_polygon="poly", stroked=True, filled=False, get_line_color=[57, 135, 229, 70], line_width_min_pixels=1, pickable=False),
        pdk.Layer("ScatterplotLayer", data=[{"lon": HKIA_LON, "lat": HKIA_LAT}], get_position="[lon, lat]", get_radius=900,
                  get_fill_color=[57, 135, 229, 90], get_line_color=[57, 135, 229, 220], stroked=True, line_width_min_pixels=1.5, pickable=False),
        pdk.Layer("TextLayer", data=[{"lon": HKIA_LON, "lat": HKIA_LAT - 0.035, "txt": "VHHH  HKIA  RWY 07L/25R 07R/25L"}], get_position="[lon, lat]",
                  get_text="txt", get_color=[180, 189, 204, 255], get_size=12, get_alignment_baseline="'top'", pickable=False,
                  font_family="Menlo, Consolas, monospace"),
        pdk.Layer("IconLayer", data=others, get_position="[lon, lat]", get_icon="icon", get_angle="angle", get_color="color",
                  get_size="size", size_units="pixels", size_min_pixels=10, size_max_pixels=22, pickable=True, billboard=False),
        pdk.Layer("IconLayer", data=tracked, get_position="[lon, lat]", get_icon="icon", get_angle="angle", get_color="color",
                  get_size="size", size_units="pixels", size_min_pixels=18, size_max_pixels=36, pickable=True, billboard=False),
    ]
    tooltip = {
        "html": "<div style='font-family:Menlo,Consolas,monospace;font-size:12px'><b>{callsign}</b> {reg} {type}<br/>{alt} · {spd}<br/>{line2}</div>",
        "style": {"backgroundColor": T.SURFACE_2, "color": T.INK, "border": f"1px solid {T.BORDER}", "borderRadius": "6px", "padding": "6px 8px"},
    }
    view = pdk.ViewState(latitude=HKIA_LAT + 0.05, longitude=HKIA_LON, zoom=7.6, pitch=0, bearing=0)
    return pdk.Deck(layers=layers, initial_view_state=view, map_style=MAP_STYLE, tooltip=tooltip)


def _legend_html() -> str:
    ramp = ", ".join(T.AMBER_RAMP)
    return (
        f"<div style='font-size:0.75rem;color:{T.INK_2};display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin-top:6px'>"
        f"<span><span style='display:inline-block;width:70px;height:8px;border-radius:4px;background:linear-gradient(90deg,{ramp});vertical-align:middle'></span>"
        f" HKIA departure · P(delay > 15) 0 → 100 %</span>"
        f"<span><span style='display:inline-block;width:10px;height:10px;border-radius:50%;background:{T.BLUE};vertical-align:middle'></span> tracked, not scored</span>"
        f"<span><span style='display:inline-block;width:70px;height:8px;border-radius:4px;background:linear-gradient(90deg,#78829a,#ecf0f6);vertical-align:middle'></span>"
        f" other traffic · altitude low → high</span>"
        f"<span style='color:{T.MUTED}'>rings: 50 / 100 nm · data: adsb.lol</span></div>")


@st.fragment(run_every="10s")
def render() -> None:
    ac, err, fetched_at = fetch_adsb(int(time.time() // 10))
    deps = candidate_departures()
    n_ac = 0 if ac is None else len(ac)
    matched = match_departures(ac, deps) if ac is not None else None
    n_tr = 0 if matched is None else int(matched["matched"].sum())
    n_dep_recent = 0
    if deps is not None and not deps.empty:
        now = pd.Timestamp.now(tz="Asia/Hong_Kong")
        act = pd.to_datetime(deps["actual_ts"], utc=True, errors="coerce").dt.tz_convert("Asia/Hong_Kong")
        n_dep_recent = int(((now - act).dt.total_seconds().between(0, 45 * 60)).sum())

    col_map, col_side = st.columns([2.5, 1.1], gap="medium")
    with col_map:
        ts = dt.datetime.fromtimestamp(fetched_at, D.HKT).strftime("%H:%M:%S") if fetched_at else "—"
        badges = T.badge(f"{n_ac} aircraft in {RADIUS_NM} nm") + T.badge(f"{n_tr} HKIA departures tracked", "ok" if n_tr else "")
        badges += T.badge("feed unavailable — showing last good frame" if ac is not None else "feed unavailable", "crit") if err else T.badge(f"adsb.lol {ts} HKT")
        st.markdown(badges, unsafe_allow_html=True)
        if ac is None:
            st.warning(f"adsb.lol feed unavailable ({err}); no cached frame yet. The map will retry every 10 s.")
        else:
            st.pydeck_chart(build_deck(matched), height=560, use_container_width=True)
        st.markdown(_legend_html(), unsafe_allow_html=True)
    with col_side:
        m1, m2 = st.columns(2)
        m1.metric("In range", f"{n_ac}", f"within {RADIUS_NM} nm", delta_color="off")
        m2.metric("Tracked", f"{n_tr}", "HKIA departures", delta_color="off")
        wx = D.weather_now()
        mt = wx["metar"]
        if mt:
            st.markdown(f"<div class='hk-strip'>{mt['raw_ob']}</div>", unsafe_allow_html=True)
        tc = wx["tc_active"]
        warn = [w for w in wx["warnings"] if w["code"] != "WTCSGNL"] if tc else wx["warnings"]
        if tc:
            st.markdown(T.badge(f"TC signal {tc[0]['signal']} {tc[0].get('tc_name') or ''}", "crit"), unsafe_allow_html=True)
        if warn:
            st.markdown("".join(T.badge(w["name"], "warn") for w in warn), unsafe_allow_html=True)
        elif not tc:
            st.markdown(T.badge("HKO: no warnings in force", "ok"), unsafe_allow_html=True)
        st.markdown("#### Tracked departures")
        if matched is not None and n_tr:
            t = matched[matched["matched"]].sort_values("sched_time")
            tbl = pd.DataFrame({"Sched": t["sched_time"], "Flight": t["flight_no"], "To": t["destination"],
                                "P(delay>15)": pd.to_numeric(t["p_delay15"], errors="coerce")})
            st.dataframe(tbl, hide_index=True, width="stretch", height=min(420, 38 + 35 * len(tbl)),
                         column_config={"P(delay>15)": st.column_config.ProgressColumn("P(>15)", min_value=0, max_value=1, format="%.2f")})
        else:
            st.caption("No HKIA departure of the last few hours is currently inside the 100 nm ring with a matching callsign. "
                       "Departures leave the ring ~15 min after take-off, so this list is usually short.")
        st.caption("Match = ICAO airline code + flight number (CPA261 ↔ CX 261). Colour = latest P(delay > 15) of that flight; "
                   "departed flights keep their last score.")
