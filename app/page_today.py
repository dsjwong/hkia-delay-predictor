"""Today's departures: tiles, timeline strip, flight table, hourly predicted vs observed."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st

import charts as C
import data as D
import theme as T
from hkia import explain as E


def _metar_parts(m: dict | None) -> tuple[str, str]:
    if not m:
        return "no METAR", ""
    wind = f"{m['wdir'] or 'VRB'}°/{m['wspd_kt']} kt" + (f" G{m['wgst_kt']}" if m.get("wgst_kt") else "")
    tail = f"{wind} · vis {m['visib']} sm" + (f" · {m['temp_c']:.0f}°C" if m.get("temp_c") is not None else "")
    return m["flt_cat"] or "?", tail


def render(fresh: dict) -> None:
    today = D.now_hkt().date()
    c1, c2 = st.columns([1, 4], vertical_alignment="bottom")
    date = c1.date_input("Date (HKT)", today, min_value=today - dt.timedelta(days=90), max_value=today + dt.timedelta(days=1))
    c2.caption(f"{date.strftime('%A %d %B %Y')} · latest cron score per flight; departed flights keep their last score so hits and misses stay visible.")
    df = D.departures(date.isoformat())
    if df.empty:
        st.info("No flights on file for that date (schedules appear ~1 day ahead).")
        return

    # -------- tiles
    wx = D.weather_now()
    scored = df["p_delay15"].notna()
    n_all, n_dep, n_can = len(df), int((df["status"] == "departed").sum()), int((df["status"] == "cancelled").sum())
    mean_p = float(df.loc[scored, "p_delay15"].mean()) if scored.any() else float("nan")
    n_hi = int((df.loc[scored, "p_delay15"] >= 0.5).sum())
    obs = df.loc[df["delay_min"].notna(), "delay_min"]
    m = wx["metar"]
    cat, tail = _metar_parts(m)
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.metric("Flights", f"{n_all:,}", f"{n_dep} departed · {n_can} cancelled", delta_color="off")
    t2.metric("Predicted > 15 min late", "—" if np.isnan(mean_p) else f"{mean_p:.0%}",
              f"mean P · {n_hi} flights with P ≥ 50 %" if scored.any() else "nothing scored yet", delta_color="off")
    t3.metric("Observed so far", f"{(obs > 15).mean():.0%}" if len(obs) else "—",
              f"> 15 min late · mean {obs.mean():.0f} min" if len(obs) else "no departures yet", delta_color="off")
    t4.metric("METAR VHHH", cat, tail or None, delta_color="off")
    tc = wx["tc_active"]
    warn = [w for w in wx["warnings"] if w["code"] != "WTCSGNL"] if tc else wx["warnings"]
    if tc:
        t5.metric("HKO", f"TC {tc[0]['signal']}", tc[0].get("tc_name") or "signal in force", delta_color="off")
    else:
        t5.metric("HKO warnings", str(len(warn)) if warn else "none", ", ".join(w["name"] for w in warn)[:40] if warn else "nothing in force", delta_color="off")
    if m:
        T.strip(f"{m['raw_ob']} &nbsp;·&nbsp; {D.fmt_hkt(m['report_time'], '%H:%M')}")
    st.markdown("#### Through the day")

    # -------- timeline + hourly
    if scored.any():
        g1, g2 = st.columns([3, 2])
        g1.plotly_chart(C.today_timeline(df), width="stretch")
        live = df[df["status"] != "cancelled"]
        byh = live.groupby("sched_hour").agg(
            n=("flight_no", "size"), p=("p_delay15", "mean"),
            n_dep=("delay_min", lambda s: int(s.notna().sum())),
            obs=("actual_delayed15", lambda s: s.dropna().astype(float).mean() if s.notna().any() else np.nan)).reset_index()
        g2.plotly_chart(C.hourly_pred_vs_obs(byh), width="stretch")

    # -------- filters + table
    st.markdown("#### Flights")
    f1, f2, f3, f4 = st.columns([2, 2, 1, 1])
    airlines = df.groupby("airline").size().sort_values(ascending=False)
    opts = [f"{D.airline_name(a)} ({a}, {n})" for a, n in airlines.items()]
    sel = f1.multiselect("Airline", opts, placeholder="all airlines")
    sel_codes = {o.split("(")[-1].split(",")[0] for o in sel}
    hr = f2.slider("Scheduled hour (HKT)", 0, 23, (0, 23))
    only_future = f3.checkbox("Not yet departed only", value=False)
    hide_can = f4.checkbox("Hide cancelled", value=True)
    v = df.copy()
    if sel_codes:
        v = v[v["airline"].isin(sel_codes)]
    v = v[(v["sched_hour"] >= hr[0]) & (v["sched_hour"] <= hr[1])]
    if only_future:
        v = v[v["status"] == "scheduled"]
    if hide_can:
        v = v[v["status"] != "cancelled"]

    hits = v["hit"].dropna()
    if len(hits):
        st.caption(f"Showing {len(v)} of {len(df)} flights · {len(hits)} departed with a score: 'P ≥ 50 % ⇔ delayed > 15 min' was right "
                   f"{hits.astype(bool).mean():.0%} of the time (observed rate {(v.loc[v['hit'].notna(), 'delay_min'] > 15).mean():.0%}) — "
                   "a 50 % cut is for eyeballing only.")
    else:
        st.caption(f"Showing {len(v)} of {len(df)} flights.")

    tbl = pd.DataFrame({
        "Sched": v["sched_time"], "Flight": v["flight_no"], "Airline": v["airline_name"], "To": v["destination"],
        "Status": v["status"], "Actual": v["actual_time"].fillna(""), "P(delay>15)": v["p_delay15"],
        "Pred delay (min)": v["pred_delay_min"], "Actual delay (min)": v["delay_min"],
        "Hit?": v["hit"].map({True: "✓", False: "✗"}).fillna(""), "Gate": v["gate"].fillna(""), "Codeshares": v["codeshares"].fillna(""),
    })
    event = st.dataframe(
        tbl, width="stretch", hide_index=True, height=min(700, 38 + 35 * len(tbl)), key="today_flights",
        on_select="rerun", selection_mode="single-row",
        column_config={
            "P(delay>15)": st.column_config.ProgressColumn("P(delay > 15 min)", min_value=0, max_value=1, format="%.2f"),
            "Pred delay (min)": st.column_config.NumberColumn(format="%.0f"),
            "Actual delay (min)": st.column_config.NumberColumn(format="%+.0f"),
        })
    st.caption("P(delay > 15) is a probability, not a verdict — 30 % means ~3 in 10 such flights leave > 15 min late. Future flights use the latest METAR, not a forecast.")
    _why_section(date.isoformat(), v, event)


def _why_section(date: str, v: pd.DataFrame, event) -> None:
    """Top-3 drivers of the selected flight's latest score (pick a row in the table above)."""
    st.markdown("#### Why this prediction")
    picked = list(getattr(getattr(event, "selection", None), "rows", []) or [])
    if not picked:
        st.caption("Select a row in the table above to see the three features that moved that flight's P(delay > 15) the most.")
        return
    r = v.iloc[picked[0]]
    rows = D.explanations(date).get((r["flight_no"], r["scheduled_ts"]), [])
    st.caption(f"**{r['flight_no']}** → {r['destination']} · scheduled {r['sched_time']} HKT · "
               + ("not scored yet" if pd.isna(r["p_delay15"]) else f"P(delay > 15) = {r['p_delay15']:.0%}"))
    T.why_lines(rows, empty="No attribution stored for this flight — they are kept for flights that have not departed yet.")
    if rows:
        st.caption(E.FOOTER)
