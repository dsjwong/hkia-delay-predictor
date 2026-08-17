"""HKIA departure-delay dashboard (M4). Reads the committed SQLite db + models/ artefacts; never scores.

  streamlit run app/streamlit_app.py --server.headless true

Pages: Today's departures | Delay patterns | Model performance | About. Times shown in HKT.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data as D  # noqa: E402  (app/data.py)

REPO = "https://github.com/dsjwong/hkia-delay-predictor"
BLUE, ORANGE, AQUA, RED, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#8a8a86"
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

st.set_page_config(page_title="HKIA delay predictor", page_icon="✈️", layout="wide")


def plotly_defaults(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=40, b=10), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(size=13), hoverlabel=dict(font_size=13))
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.2)", zeroline=False)
    return fig


def p_badge(p: float | None) -> str:
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "—"
    return f"{p:.0%}"


# ------------------------------------------------------------------ sidebar
if not D.db_available():
    st.error(f"Database not found at `{D.DB_PATH}`. On Streamlit Cloud this is the committed `data/hkia.db`; locally run "
             "`python scripts/ingest_all.py --backfill` first.")
    st.stop()

fresh = D.freshness()
st.sidebar.title("HKIA delay predictor")
page = st.sidebar.radio("Page", ["Today's departures", "Delay patterns", "Model performance", "About"], label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Data as of** {D.fmt_hkt(fresh['last_ingest'])}  \n"
                    f"last score {D.fmt_hkt(fresh['pred_scored'], '%H:%M')} · METAR {D.fmt_hkt(fresh['metar_report'], '%H:%M')}")
st.sidebar.caption(f"{fresh['n_flights']:,} departures on file, {fresh['date_min']} → {fresh['date_max']}. "
                   "Refreshed by a GitHub Actions cron every 30 min; the page re-reads the db every 10 min.")
st.sidebar.markdown(f"[Source on GitHub]({REPO})")


# ------------------------------------------------------------------ page 1: today's departures
def page_today() -> None:
    today = D.now_hkt().date()
    c1, c2 = st.columns([1, 3])
    date = c1.date_input("Date (HKT)", today, min_value=today - dt.timedelta(days=90), max_value=today + dt.timedelta(days=1))
    st.title(f"HKIA departures — {date.strftime('%a %d %b %Y')}")
    st.caption(f"Data as of **{D.fmt_hkt(fresh['last_ingest'])}**. P(delay > 15) and predicted minutes come from the "
               "latest cron score of each not-yet-departed flight; departed flights keep their last score so you can see hits and misses.")
    df = D.departures(date.isoformat())
    if df.empty:
        st.info("No flights on file for that date (schedules appear ~1 day ahead).")
        return

    # -------- summary tiles
    wx = D.weather_now()
    scored = df["p_delay15"].notna()
    n_all, n_dep, n_can = len(df), int((df["status"] == "departed").sum()), int((df["status"] == "cancelled").sum())
    mean_p = float(df.loc[scored, "p_delay15"].mean()) if scored.any() else float("nan")
    n_hi = int((df.loc[scored, "p_delay15"] >= 0.5).sum())
    obs = df.loc[df["delay_min"].notna(), "delay_min"]
    m = wx["metar"]
    metar_txt = "no METAR"
    if m:
        wind = f"{m['wdir'] or 'VRB'}°/{m['wspd_kt']} kt" + (f" G{m['wgst_kt']}" if m.get("wgst_kt") else "")
        metar_txt = f"{m['flt_cat'] or '?'} · {wind} · vis {m['visib']} sm" + (f" · {m['temp_c']:.0f}°C" if m.get("temp_c") is not None else "")
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.metric("Flights", f"{n_all:,}", f"{n_dep} departed · {n_can} cancelled", delta_color="off")
    t2.metric("Predicted share > 15 min late", "—" if np.isnan(mean_p) else f"{mean_p:.0%}",
              f"mean P over {int(scored.sum())} scored · {n_hi} with P ≥ 50 %" if scored.any() else "nothing scored yet", delta_color="off")
    t3.metric("Observed so far", f"{(obs > 15).mean():.0%} > 15 min" if len(obs) else "—",
              f"mean {obs.mean():.0f} min over {len(obs)}" if len(obs) else "no departures yet", delta_color="off")
    t4.metric("METAR VHHH", metar_txt.split(" · ")[0], " · ".join(metar_txt.split(" · ")[1:]) or None, delta_color="off")
    if m:
        t4.caption(f"{m['raw_ob']}  \n{D.fmt_hkt(m['report_time'], '%H:%M')}")
    tc = wx["tc_active"]
    warn = [w for w in wx["warnings"] if w["code"] != "WTCSGNL"] if tc else wx["warnings"]
    if tc:
        t5.metric("HKO", f"TC signal {tc[0]['signal']}", tc[0].get("tc_name") or "", delta_color="off")
    else:
        t5.metric("HKO warnings", str(len(warn)) if warn else "none", None)
    if warn:
        t5.caption(", ".join(w["name"] for w in warn))
    elif not tc:
        t5.caption("no warnings in force")

    # -------- filters
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
        st.caption(f"Showing {len(v)} of {len(df)} flights · among the {len(hits)} departed flights with a score, "
                   f"'P ≥ 50 % ⇔ delayed > 15 min' was right {hits.astype(bool).mean():.0%} of the time "
                   f"(observed delayed rate {(v.loc[v['hit'].notna(), 'delay_min'] > 15).mean():.0%}). "
                   "A 50 % cut is just for eyeballing — the model outputs probabilities, see Model performance.")
    else:
        st.caption(f"Showing {len(v)} of {len(df)} flights.")

    tbl = pd.DataFrame({
        "Sched": v["sched_time"], "Flight": v["flight_no"], "Airline": v["airline_name"], "To": v["destination"],
        "Status": v["status"].map({"scheduled": "scheduled", "departed": "departed", "cancelled": "cancelled"}),
        "Actual": v["actual_time"].fillna(""), "P(delay>15)": v["p_delay15"],
        "Pred delay (min)": v["pred_delay_min"], "Actual delay (min)": v["delay_min"],
        "Hit?": v["hit"].map({True: "✓", False: "✗"}).fillna(""),
        "Gate": v["gate"].fillna(""), "Codeshares": v["codeshares"].fillna(""),
    })
    st.dataframe(
        tbl, width="stretch", hide_index=True, height=min(900, 38 + 35 * len(tbl)),
        column_config={
            "P(delay>15)": st.column_config.ProgressColumn("P(delay > 15 min)", min_value=0, max_value=1, format="%.2f"),
            "Pred delay (min)": st.column_config.NumberColumn(format="%.0f"),
            "Actual delay (min)": st.column_config.NumberColumn(format="%+.0f"),
        })
    st.caption("P(delay > 15) is a probability, not a verdict: 30 % means roughly 3 in 10 such flights leave more than 15 min late. "
               "Weather used for future flights = latest METAR (persistence), not a forecast.")

    # -------- by-hour strip
    if scored.any():
        byh = df[df["status"] != "cancelled"].groupby("sched_hour").agg(
            n=("flight_no", "size"), p=("p_delay15", "mean"),
            obs=("actual_delayed15", lambda s: s.dropna().astype(float).mean() if s.notna().any() else np.nan)).reset_index()
        fig = go.Figure()
        fig.add_bar(x=byh["sched_hour"], y=byh["p"], name="mean P(delay > 15) predicted", marker_color=BLUE,
                    hovertemplate="%{x}:00 · P=%{y:.0%}<extra>predicted</extra>")
        fig.add_scatter(x=byh["sched_hour"], y=byh["obs"], mode="markers", name="observed share > 15 min (departed)",
                        marker=dict(color=ORANGE, size=9, line=dict(color="white", width=1)),
                        hovertemplate="%{x}:00 · %{y:.0%}<extra>observed</extra>")
        fig.update_layout(title="By scheduled hour: predicted vs observed", yaxis_tickformat=".0%",
                          xaxis=dict(dtick=1, title="hour (HKT)"), legend=dict(orientation="h", y=1.12))
        st.plotly_chart(plotly_defaults(fig, 320), width="stretch")


# ------------------------------------------------------------------ page 2: delay patterns
def page_patterns() -> None:
    st.title("Delay patterns — last 91 days")
    h = D.history()
    if h.empty:
        st.info("No departed flights in the window yet.")
        return
    st.caption(f"{len(h):,} departed passenger flights, {h['date'].min()} → {h['date'].max()} (rolling window kept by the "
               f"data.gov.hk API; delays clipped to [-60, 600] min like the training set). Overall: mean delay "
               f"**{h['delay_min'].mean():.1f} min**, median **{h['delay_min'].median():.0f} min**, "
               f"**{h['delayed15'].mean():.0%}** later than 15 min.")

    metric = st.radio("Heatmap metric", ["Mean delay (min)", "% delayed > 15 min"], horizontal=True)
    grid = h.pivot_table(index="dow", columns="hour", values="delay_min" if metric.startswith("Mean") else "delayed15", aggfunc="mean")
    grid = grid.reindex(index=range(7), columns=range(24))
    z = grid.to_numpy()
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"{hh:02d}" for hh in range(24)], y=DOW, colorscale="Blues", xgap=2, ygap=2,
        colorbar=dict(title="min" if metric.startswith("Mean") else "%", tickformat="" if metric.startswith("Mean") else ".0%"),
        hovertemplate="%{y} %{x}:00 · %{z:.1f}<extra></extra>" if metric.startswith("Mean") else "%{y} %{x}:00 · %{z:.0%}<extra></extra>"))
    fig.update_layout(title=f"{metric} by scheduled hour (HKT) × day of week", xaxis_title="hour", yaxis_autorange="reversed")
    st.plotly_chart(plotly_defaults(fig, 360), width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Airlines (n ≥ 50)")
        a = h.groupby("airline").agg(n=("delay_min", "size"), mean_delay=("delay_min", "mean"), pct15=("delayed15", "mean")).reset_index()
        a = a[a["n"] >= 50].sort_values("pct15", ascending=False)
        a.insert(1, "name", a["airline"].map(D.airline_name))
        st.dataframe(a.rename(columns={"airline": "code", "mean_delay": "mean delay (min)", "pct15": "% > 15 min"}),
                     hide_index=True, width="stretch", height=420,
                     column_config={"mean delay (min)": st.column_config.NumberColumn(format="%.1f"),
                                    "% > 15 min": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
    with c2:
        st.markdown("#### Top destinations (by flights)")
        d = h.groupby("dest1").agg(n=("delay_min", "size"), mean_delay=("delay_min", "mean"), pct15=("delayed15", "mean")).reset_index()
        d = d.sort_values("n", ascending=False).head(25)
        st.dataframe(d.rename(columns={"dest1": "IATA", "mean_delay": "mean delay (min)", "pct15": "% > 15 min"}),
                     hide_index=True, width="stretch", height=420,
                     column_config={"mean delay (min)": st.column_config.NumberColumn(format="%.1f"),
                                    "% > 15 min": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})

    td = D.typhoon_days()
    if not td.empty and (td["signal"] > 0).any():
        sig, no = td[td["signal"] > 0], td[td["signal"] == 0]
        names = ", ".join(sorted({f"{n} ({', '.join(sorted(sig.loc[sig['tc_name'] == n, 'date']))})" for n in sig["tc_name"].dropna()}))
        s8 = sig[sig["signal"] >= 8]
        msg = (f"**Typhoon days in the window** — {len(sig)} day(s) with a tropical-cyclone signal in force ({names}): "
               f"mean delay **{sig['mean_delay'].mean():.0f} min**, {sig['pct15'].mean():.0%} > 15 min, "
               f"vs **{no['mean_delay'].mean():.0f} min**, {no['pct15'].mean():.0%} on the other {len(no)} days.")
        if len(s8):
            msg += f" Signal 8+ days only: mean {s8['mean_delay'].mean():.0f} min ({', '.join(s8['date'])})."
        st.warning(msg + " Handful of days — anecdotal, not a measured effect.")

    daily = td if not td.empty else h.groupby("date").agg(mean_delay=("delay_min", "mean"), pct15=("delayed15", "mean")).reset_index()
    fig = go.Figure()
    fig.add_bar(x=daily["date"], y=daily["mean_delay"], marker_color=[ORANGE if s > 0 else BLUE for s in daily.get("signal", pd.Series(0, index=daily.index))],
                hovertemplate="%{x} · %{y:.0f} min<extra></extra>", name="mean delay")
    fig.update_layout(title="Mean departure delay per day (orange = TC signal in force)", yaxis_title="min", showlegend=False)
    st.plotly_chart(plotly_defaults(fig, 300), width="stretch")


# ------------------------------------------------------------------ page 3: model performance
def page_model() -> None:
    st.title("Model performance")
    man = D.manifest()
    if not man:
        st.info("models/MANIFEST.json not found.")
        return
    sp = man["split"]
    st.caption(f"XGBoost trained {man['created_at'][:10]} (git `{man['git_sha']}`, xgboost {man['xgboost']}, {len(man['features'])} features). "
               f"Date-ordered split, no shuffling: train {sp['train']['date_min']}→{sp['train']['date_max']} ({sp['train']['n_rows']:,}), "
               f"val {sp['val']['date_min']}→{sp['val']['date_max']} ({sp['val']['n_rows']:,}), "
               f"**test {sp['test']['date_min']}→{sp['test']['date_max']} ({sp['test']['n_rows']:,} departures)**.")

    st.markdown("#### Held-out test metrics (baselines vs model)")
    rows = {"A: global rate / mean": "A_global/test", "B: airline × hour mean (train only)": "B_airline_hour/test",
            "train median delay": "median_train/test", "XGBoost": "XGB/test"}
    met = pd.DataFrame([{"predictor": k, **man["metrics"].get(v, {})} for k, v in rows.items()])
    met = met.rename(columns={"auc": "AUC ↑", "logloss": "log loss ↓", "brier": "Brier ↓", "mae": "MAE min ↓"})
    st.dataframe(met, hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="%.3f") for c in met.columns if c != "predictor"})
    x = man["metrics"]["XGB/test"]; b = man["metrics"]["B_airline_hour/test"]
    st.markdown(f"**How to read this.** AUC {x['auc']:.3f} means: pick a random delayed and a random on-time flight, the model ranks "
                f"the delayed one higher {x['auc']:.0%} of the time (0.5 = coin flip; the airline × hour lookup gets {b['auc']:.0%}). "
                f"Log loss / Brier reward calibrated probabilities. MAE {x['mae']:.1f} min is the typical error in predicted delay minutes "
                f"vs {b['mae']:.1f} for the baseline and {man['metrics']['median_train/test']['mae']:.1f} for 'always predict the median'. "
                "Delays are heavy-tailed, so these are modest, honest gains — not a crystal ball.")

    c1, c2 = st.columns(2)
    with c1:
        cal = D.calibration_from_report()
        if not cal.empty:
            fig = go.Figure()
            fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=GREY, dash="dot", width=1.5), name="perfect", hoverinfo="skip")
            fig.add_scatter(x=cal["pred_mean"], y=cal["obs_rate"], mode="lines+markers", name="XGB (test)",
                            marker=dict(size=np.clip(np.sqrt(cal["n"]) * 0.6, 6, 26), color=BLUE, line=dict(color="white", width=1)),
                            line=dict(color=BLUE, width=2), customdata=cal["n"],
                            hovertemplate="predicted %{x:.2f} · observed %{y:.2f} · n=%{customdata}<extra></extra>")
            fig.update_layout(title="Calibration on test (marker size ~ bin count)", xaxis_title="mean predicted P(delay > 15)",
                              yaxis_title="observed rate", xaxis_range=[0, 1], yaxis_range=[0, 1], legend=dict(orientation="h", y=1.12))
            st.plotly_chart(plotly_defaults(fig, 380), width="stretch")
    with c2:
        fi = D.feature_importance()
        if fi:
            which = st.radio("Model", ["P(delay > 15) classifier", "delay-minutes regressor"], horizontal=True, label_visibility="collapsed")
            imp = pd.Series(fi["clf_delayed15" if which.startswith("P(") else "reg_delay_min"]).sort_values()
            fig = go.Figure(go.Bar(x=imp.values, y=imp.index, orientation="h", marker_color=BLUE,
                                   hovertemplate="%{y}: gain %{x:.1f}<extra></extra>"))
            fig.update_layout(title="Feature importance (XGBoost gain, top 15)", xaxis_title="gain")
            st.plotly_chart(plotly_defaults(fig, 380), width="stretch")
    ab = pd.DataFrame(man.get("ablation_test", {})).T.reset_index().rename(columns={"index": "variant"})
    with st.expander("Ablation on test — remove a feature group"):
        st.dataframe(ab, hide_index=True, width="stretch")
        st.caption("Weather is worth ~+0.013 AUC in a test window without a typhoon; the point-in-time rolling delay features do not help AUC on test.")

    st.markdown("#### Live evaluation — predictions vs what actually happened")
    ev = D.live_eval(7)
    if ev["status"] != "ok":
        st.info(f"Collecting — **{ev['n_matured']}** matured predictions so far (need ≥ {ev['min_n']}). A prediction 'matures' when its "
                "flight departs; the metric is the last score written before departure. The cron started scoring on 2026-08-17, "
                "so a week of numbers appears after a few days.")
    else:
        st.caption(f"Flights departed {ev['date_min']} → {ev['date_max']} (last {ev['window_days']} days), n = {ev['n_matured']}, "
                   f"observed P(delay > 15) = {ev['delayed15_rate']:.2f}, median lead time between last score and departure "
                   f"{ev['median_lead_min']:.0f} min.")
        rows = []
        for k, label in (("model", "XGBoost (live)"), ("baseline_airline_hour", "airline × hour baseline"), ("naive_rate", "observed rate / median")):
            m = ev.get(k, {})
            if m and "error" not in m:
                rows.append({"predictor": label, "AUC ↑": m.get("auc"), "Brier ↓": m.get("brier"), "log loss ↓": m.get("logloss"), "MAE min ↓": m.get("mae")})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    with st.expander("Interpretation from the M2 report"):
        st.markdown(D.report_interpretation() or "_reports/M2-results.md not found_")

    st.markdown("#### Limitations")
    st.markdown(
        "- **Weather = latest observation, not a forecast.** Every future flight is scored with the most recent VHHH METAR "
        "(persistence, capped at 3 h of age). A storm forecast for the evening does not move the morning's numbers.\n"
        "- **Departures only, no arrivals, no ADS-B.** The single strongest real-world predictor — the inbound aircraft running late — "
        "is not in the model yet (OpenSky is a stretch goal).\n"
        "- **Rolling 91-day window, one season.** The data.gov.hk API keeps ~91 days; the training set (May–Aug 2026) has one typhoon "
        "(Noul, 25–26 Jul) in the validation split, so typhoon effects are learned from a handful of days and unconfirmed on test.\n"
        "- **Survivorship / churn.** Cancelled flights are excluded from the delay label; the schedule for tomorrow can still change.\n"
        "- **Staleness.** Predictions come from a 30-min cron; between runs they can be up to 30 min old (see 'data as of').")


# ------------------------------------------------------------------ page 4: about
def page_about() -> None:
    st.title("About")
    st.markdown(f"""
**What** — for every HKIA passenger departure, the probability it leaves more than 15 min late and the expected delay in minutes,
from live schedule + weather data, with an honest evaluation page. Departures only (v1).

**Architecture (10 lines)**
1. GitHub Actions cron (`ingest.yml`, every 30 min, $0) checks out this repo.
2. `hkia.ingest_flights` pulls yesterday/today/tomorrow's departures from the Airport Authority flight-info API on data.gov.hk (scheduled vs actual = the label).
3. `hkia.ingest_weather` pulls the latest VHHH METAR (aviationweather.gov) and HKO current readings + warnings (typhoon signals) into SQLite `data/hkia.db`.
4. `hkia.features` builds the same 33 features for training and inference (calendar, airline/destination, congestion, as-of weather, point-in-time rolling delays).
5. `hkia.train` (offline, occasionally) fits baselines + XGBoost on a date-ordered split → `models/`, `reports/M2-results.md`.
6. `hkia.predict` (every cron run) scores every not-yet-departed flight for today + tomorrow → table `predictions` (history kept).
7. A daily job (`backfill.yml`) tops up METAR history (IEM) + typhoon-signal history and runs `hkia.evaluate` (last score before departure vs actual).
8. The bot commits `data/hkia.db` back to `main` — the db in git *is* the data store.
9. `hkia.api` (FastAPI) serves the same tables read-only; this Streamlit page reads the db directly.
10. Streamlit Community Cloud redeploys from `main`, so each bot commit refreshes this page.

**Data sources**
- [HKIA flight information — data.gov.hk / Airport Authority](https://data.gov.hk/en-data/dataset/aahk-team1-flight-info) (real-time + ~91-day history)
- [Hong Kong Observatory Open Data API](https://data.gov.hk/en-data/dataset/hk-hko-rss-current-weather-report) (current readings, warnings, TC signals) and the [HKO warning database](https://www.hko.gov.hk/en/wxinfo/climat/warndb/warndb1.shtml)
- [aviationweather.gov METAR](https://aviationweather.gov/data/api/) for VHHH; historical METAR from the [IEM ASOS archive](https://mesonet.agron.iastate.edu/request/download.phtml)

**Code** — [{REPO.replace('https://', '')}]({REPO}) · README has the run book, `reports/M2-results.md` the numbers, `docs/features.md` the feature dictionary.

**Author** — Darren Wong, HKUST CS + AI. Built as a genuine-interest aviation + ML project and an ML-engineering showcase.
""")


{"Today's departures": page_today, "Delay patterns": page_patterns, "Model performance": page_model, "About": page_about}[page]()
