"""Model performance. Leads with the live report card (how the published predictions actually scored), then the
held-out test metrics, reliability diagram, feature importance, ablation, the full live metric table and limitations."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import charts as C
import data as D


def _f(x, nd=3, dash="—") -> str:
    return dash if x is None or x != x else f"{x:.{nd}f}"


def _daily_df(ev: dict) -> pd.DataFrame:
    return pd.DataFrame([{"date": r["date"], "n": r["n"], "delayed15_rate": r["delayed15_rate"], "thin": r["thin"],
                          "partial": r.get("partial", False), "model_auc": r["model"]["auc"], "model_mae": r["model"]["mae"],
                          "baseline_auc": (r.get("baseline") or {}).get("auc")} for r in ev.get("daily") or []])


def _bucket_df(ev: dict) -> pd.DataFrame:
    return pd.DataFrame([{"label": r["label"], "n": r["n"], "thin": r["thin"], "model_auc": r["model"]["auc"],
                          "baseline_auc": (r.get("baseline") or {}).get("auc")} for r in ev.get("lead_buckets") or []])


def _delta_caption(ev: dict, key: str, nd: int = 3, unit: str = "") -> str | None:
    """`+0.017 vs baseline 0.647` — with the bootstrap interval, and the words "within noise" when it straddles 0.

    A delta reported without its interval is the single most misleading thing this page could do: +0.017 AUC on four
    days of flights looks like a win and is not one.
    """
    d = (ev.get("deltas") or {}).get(key)
    if d is None:
        return None
    b = (ev.get("baseline_airline_hour") or {}).get(key)
    out = f"{d:+.{nd}f}{unit} vs baseline {_f(b, nd)}"
    bs = ev.get("bootstrap") or {}
    ci = (bs.get("ci") or {}).get(key)
    if ci:
        out += f" · 95 % CI {ci[0]:+.{nd}f}…{ci[1]:+.{nd}f}"
        if not (bs.get("beats_baseline") or {}).get(key):
            out += " (within noise)"
    return out


def _verdict(ev: dict) -> str:
    labels = {"auc": "AUC", "brier": "Brier", "logloss": "log loss", "mae": "MAE"}
    bs = ev.get("bootstrap") or {}
    if not bs:
        return "on this much data the margins should be read as provisional."
    won = [labels[k] for k in ("auc", "brier", "logloss", "mae") if (bs.get("beats_baseline") or {}).get(k)]
    return (f"on this window the model is separably better on {', '.join(won)}; the rest are inside the noise."
            if won else "on this window none of the margins clear the noise yet.")


def _notable_df(rows: list[dict]) -> pd.DataFrame:
    """One row per flight; the outcome carries a ✓/✗ mark as well as its wording, never colour alone."""
    out = []
    for r in rows:
        late = r["delayed15"] == 1
        called = ((r["p"] or 0) >= 0.5) == late
        out.append({"flight": r["flight_no"], "date": r["date"][5:], "to": r["dest"] or "—",
                    "P(delay > 15)": r["p"], "pred min": r["pred_min"],
                    "outcome": f"{'✓' if called else '✗'} " + (f"{r['delay_min']:+.0f} min late" if late else "on time")})
    return pd.DataFrame(out)


def _notable_table(rows: list[dict], title: str) -> None:
    st.markdown(f"###### {title}")
    df = _notable_df(rows)
    if df.empty:
        st.caption("no flights in this slice yet")
        return
    st.dataframe(df, hide_index=True, width="stretch", column_config={
        "P(delay > 15)": st.column_config.ProgressColumn(min_value=0.0, max_value=1.0, format="%.2f"),
        "pred min": st.column_config.NumberColumn(format="%.1f")})


def _report_card(ev: dict) -> None:
    """The live report card: what the published predictions were actually worth, graded after the flights departed."""
    st.markdown("#### Model report card — live, graded after the fact")
    if str(ev.get("status", "")).startswith("error"):   # a broken pipeline must not look like a young one
        st.error(f"The live evaluation could not be computed: {ev['status']}")
        return
    if ev["status"] != "ok":
        st.info(f"Collecting — **{ev['n_matured']}** matured predictions so far (need ≥ {ev['min_n']}). A prediction matures when its "
                "flight departs; the metric uses the last score written before departure. Scoring started 2026-08-17.")
        return
    m, b, d = ev.get("model", {}), ev.get("baseline_airline_hour", {}), ev.get("deltas") or {}
    has_b = "error" not in b
    st.caption(f"Rolling {ev['window_days']}-day window · flights departed {ev['date_min']} → {ev['date_max']} · "
               f"n = {ev['n_matured']:,} · observed P(delay > 15) = {ev['delayed15_rate']:.2f} · median lead time between the last "
               f"score and departure {ev['median_lead_min']:.0f} min · computed {ev.get('computed_at', '')[:16].replace('T', ' ')} UTC")
    k1, k2, k3, k4 = st.columns(4)
    # delta_color="off" for a margin whose CI straddles 0: green would claim a win the data does not support
    sig = (ev.get("bootstrap") or {}).get("beats_baseline") or {}
    k1.metric("AUC (live)", _f(m.get("auc")), _delta_caption(ev, "auc"), delta_color="normal" if sig.get("auc") else "off")
    k2.metric("Brier", _f(m.get("brier")), _delta_caption(ev, "brier"), delta_color="inverse" if sig.get("brier") else "off")
    k3.metric("MAE (min)", _f(m.get("mae"), 1), _delta_caption(ev, "mae", 1, " min"),
              delta_color="inverse" if sig.get("mae") else "off")
    cov = ev.get("coverage") or {}
    k4.metric("Matured predictions", f"{ev['n_matured']:,}",
              f"{cov['pct']:.0%} of the {cov['n_departed']:,} departures {ev['date_min'][5:]} → {ev['date_max'][5:]}"
              if cov.get("pct") is not None else f"{ev['window_days']}-day window · {ev['date_min'][5:]} → {ev['date_max'][5:]}")

    c1, c2 = st.columns(2)
    with c1:
        daily = _daily_df(ev)
        if daily.empty:
            st.info("No daily series in this snapshot — re-run `python -m hkia.evaluate`.")
        else:
            st.plotly_chart(C.live_daily_auc(daily), width="stretch")
            part = [r["date"][5:] for r in ev["daily"] if r.get("partial")]
            if part:   # the window's first and last dates are truncated: not comparable with a full day
                st.caption(f"{' and '.join(part)} {'are' if len(part) > 1 else 'is'} a partial day — the rolling window "
                           "starts and ends part-way through a date, so those points cover fewer flights.")
    with c2:
        buckets = _bucket_df(ev)
        if buckets.empty:
            st.info("No lead-time buckets in this snapshot — re-run `python -m hkia.evaluate`.")
        else:
            st.plotly_chart(C.lead_bucket_bars(buckets), width="stretch")
            thin = [r["label"] for r in ev["lead_buckets"] if r["thin"]]
            st.caption("Minutes between the last score and the **scheduled** departure. Deliberately not the actual one: "
                       "`actual − scored` is a function of the delay itself (a flight is only ever scored six hours before "
                       "it left because it left six hours late), so bucketing on it would stratify by the outcome. "
                       "`after STD` = the score landed after the scheduled time, i.e. the flight was already visibly late."
                       + (f" Thin buckets (< {ev.get('min_slice_n', 100)} flights, AUC is mostly noise): {', '.join(thin)}." if thin else ""))

    c3, c4 = st.columns(2)
    with c3:
        cal = pd.DataFrame(ev.get("calibration") or [])
        if cal.empty:
            st.info("No live calibration in this snapshot — re-run `python -m hkia.evaluate`.")
        else:
            st.plotly_chart(C.reliability(cal, "XGBoost (live)", "Calibration on live data (10 equal-width bins)",
                                          min_n=ev.get("cal_min_n", 30)), width="stretch")
            st.caption(f"Bins under {ev.get('cal_min_n', 30)} flights are drawn hollow and left unconnected — an observed "
                       "rate on six flights moves 17 points per flight.")
    with c4:
        st.markdown("###### How this is computed")
        st.markdown(
            f"Every 30 minutes a GitHub Actions cron scores every departure that has not left yet and appends the probability to the "
            f"database. When the aircraft finally departs, that prediction *matures*: the **last score written before the actual "
            f"departure time** is locked in and compared with the real delay (actual − scheduled, > 15 min = late). Everything above "
            f"is the rolling **{ev['window_days']}-day window** of those matured predictions — {ev['n_matured']:,} flights that departed "
            f"{ev['date_min']} → {ev['date_max']}, of which {ev['delayed15_rate']:.0%} were more than 15 minutes late. The comparison is "
            f"the same baseline used at training time: the **airline × hour lookup table** — the historical delay rate for that airline in "
            f"that hour of day, fitted on the training split only, with no weather and no congestion.")
        cov = ev.get("coverage") or {}
        coverage = (f"Coverage is {cov['pct']:.0%} — {cov['n_scored']:,} of the {cov['n_departed']:,} departures on those dates were "
                    "scored in time; the rest are excluded and are not a random sample (the cron tends to miss the flights that left "
                    "promptly), so the late rate above is the rate among scored flights. " if cov.get("pct") is not None else "")
        st.caption("Nothing here is a back-test: these are the numbers the site actually showed, graded after the fact. "
                   + coverage
                   + f"Slices with fewer than {ev.get('min_slice_n', 100)} flights are labelled thin because their AUC is mostly noise, "
                   + f"and every margin carries a 95 % paired-bootstrap interval — {_verdict(ev)}")

    nb = ev.get("notable") or {}
    st.markdown(f"###### Notable flights of the last {ev['window_days']} days")
    st.caption("The calls the model got most right, and the ones it got most wrong — same window, same last-score-before-departure rule.")
    n1, n2 = st.columns(2)
    with n1:
        _notable_table(nb.get("confident_correct") or [], "Confident and correct — high P, and they were late")
        hc = nb.get("high_confidence") or {}
        if hc.get("n"):
            st.caption(f"That table is picked *after* the fact, so it can only contain wins. The honest counterpart: of "
                       f"**all {hc['n']} calls published at P ≥ {hc['threshold']:.0%}**, {hc['n_late']} were more than 15 minutes "
                       f"late ({hc['rate']:.0%}).")
    with n2:
        _notable_table(nb.get("worst_misses") or [], "Biggest misses — both directions")
    if not has_b:
        st.caption("The airline × hour baseline table is not available in this checkout, so the baseline series are omitted.")
    st.divider()


def render() -> None:
    man = D.manifest()
    if not man:
        st.info("models/MANIFEST.json not found.")
        return
    sp = man["split"]
    st.caption(f"XGBoost trained {man['created_at'][:10]} (git `{man['git_sha']}`, xgboost {man['xgboost']}, {len(man['features'])} features). "
               f"Date-ordered split, no shuffling: train {sp['train']['date_min']}→{sp['train']['date_max']} ({sp['train']['n_rows']:,}), "
               f"val {sp['val']['date_min']}→{sp['val']['date_max']} ({sp['val']['n_rows']:,}), "
               f"**test {sp['test']['date_min']}→{sp['test']['date_max']} ({sp['test']['n_rows']:,} departures)**.")

    ev = D.live_eval(7)
    _report_card(ev)

    x = man["metrics"]["XGB/test"]; b = man["metrics"]["B_airline_hour/test"]; med = man["metrics"]["median_train/test"]
    st.markdown("#### Held-out test — XGBoost vs airline × hour baseline")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("AUC", f"{x['auc']:.3f}", f"{x['auc'] - b['auc']:+.3f} vs baseline {b['auc']:.3f}")
    k2.metric("Brier", f"{x['brier']:.3f}", f"{x['brier'] - b['brier']:+.3f} vs baseline {b['brier']:.3f}", delta_color="inverse")
    k3.metric("Log loss", f"{x['logloss']:.3f}", f"{x['logloss'] - b['logloss']:+.3f} vs baseline {b['logloss']:.3f}", delta_color="inverse")
    k4.metric("MAE (min)", f"{x['mae']:.1f}", f"{x['mae'] - b['mae']:+.1f} vs baseline {b['mae']:.1f} · median {med['mae']:.1f}", delta_color="inverse")
    st.caption(f"AUC {x['auc']:.3f} = a random delayed flight is ranked above a random on-time one {x['auc']:.0%} of the time (coin flip 50 %, "
               f"airline × hour lookup {b['auc']:.0%}); Brier / log loss reward calibration; MAE is the typical error in minutes. Modest, honest gains.")
    rows = {"A: global rate / mean": "A_global/test", "B: airline × hour mean (train only)": "B_airline_hour/test",
            "train median delay": "median_train/test", "XGBoost": "XGB/test"}
    met = pd.DataFrame([{"predictor": k, **man["metrics"].get(v, {})} for k, v in rows.items()])
    met = met.rename(columns={"auc": "AUC ↑", "logloss": "log loss ↓", "brier": "Brier ↓", "mae": "MAE min ↓"})
    with st.expander("Full metric table — all baselines"):
        st.dataframe(met, hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="%.3f") for c in met.columns if c != "predictor"})

    c1, c2 = st.columns(2)
    with c1:
        cal = D.calibration_from_report()
        if not cal.empty:
            st.plotly_chart(C.reliability(cal), width="stretch")
    with c2:
        fi = D.feature_importance()
        if fi:
            which = st.radio("Model", ["P(delay > 15) classifier", "delay-minutes regressor"], horizontal=True, label_visibility="collapsed")
            imp = pd.Series(fi["clf_delayed15" if which.startswith("P(") else "reg_delay_min"]).sort_values()
            st.plotly_chart(C.importance_hbar(imp, "Feature importance (XGBoost gain, top 15)"), width="stretch")
    ab = pd.DataFrame(man.get("ablation_test", {})).T.reset_index().rename(columns={"index": "variant"})
    with st.expander("Ablation on test — remove a feature group"):
        st.dataframe(ab, hide_index=True, width="stretch")
        st.caption("Weather is worth ~+0.013 AUC in a test window without a typhoon; the point-in-time rolling delay features do not help AUC on test.")

    st.markdown("#### Live evaluation — full metric table")
    if ev["status"] != "ok":
        st.info(f"Collecting — **{ev['n_matured']}** matured predictions so far (need ≥ {ev['min_n']}).")
    else:
        st.caption(f"The same rolling {ev['window_days']}-day window as the report card, with log loss and the naive predictors "
                   "(“always the observed rate” / “always the median delay”) for reference.")
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
        "- **Departures only, no arrivals, no ADS-B in the model.** The single strongest real-world predictor — the inbound aircraft running late — "
        "is not a feature yet (the live map shows ADS-B but does not feed the model).\n"
        "- **Rolling 91-day window, one season.** The data.gov.hk API keeps ~91 days; the training set (May–Aug 2026) has one typhoon "
        "(Noul, 25–26 Jul) in the validation split, so typhoon effects are learned from a handful of days and unconfirmed on test.\n"
        "- **Survivorship / churn.** Cancelled flights are excluded from the delay label; the schedule for tomorrow can still change.\n"
        "- **Staleness.** Predictions come from a 30-min cron; between runs they can be up to 30 min old (see 'data as of').")
