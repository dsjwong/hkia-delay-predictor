"""Model performance: metric tiles, reliability diagram, feature importance, ablation, live evaluation, limitations."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import charts as C
import data as D


def render() -> None:
    man = D.manifest()
    if not man:
        st.info("models/MANIFEST.json not found.")
        return
    sp = man["split"]
    st.markdown("### Model performance")
    st.caption(f"XGBoost trained {man['created_at'][:10]} (git `{man['git_sha']}`, xgboost {man['xgboost']}, {len(man['features'])} features). "
               f"Date-ordered split, no shuffling: train {sp['train']['date_min']}→{sp['train']['date_max']} ({sp['train']['n_rows']:,}), "
               f"val {sp['val']['date_min']}→{sp['val']['date_max']} ({sp['val']['n_rows']:,}), "
               f"**test {sp['test']['date_min']}→{sp['test']['date_max']} ({sp['test']['n_rows']:,} departures)**.")

    x = man["metrics"]["XGB/test"]; b = man["metrics"]["B_airline_hour/test"]; med = man["metrics"]["median_train/test"]
    st.markdown("#### Held-out test — XGBoost vs airline × hour baseline")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("AUC", f"{x['auc']:.3f}", f"{x['auc'] - b['auc']:+.3f} vs baseline {b['auc']:.3f}")
    k2.metric("Brier", f"{x['brier']:.3f}", f"{x['brier'] - b['brier']:+.3f} vs baseline {b['brier']:.3f}", delta_color="inverse")
    k3.metric("Log loss", f"{x['logloss']:.3f}", f"{x['logloss'] - b['logloss']:+.3f} vs baseline {b['logloss']:.3f}", delta_color="inverse")
    k4.metric("MAE (min)", f"{x['mae']:.1f}", f"{x['mae'] - b['mae']:+.1f} vs baseline {b['mae']:.1f} · median {med['mae']:.1f}", delta_color="inverse")
    st.caption(f"AUC {x['auc']:.3f}: pick a random delayed and a random on-time flight, the model ranks the delayed one higher {x['auc']:.0%} "
               f"of the time (0.5 = coin flip; the airline × hour lookup gets {b['auc']:.0%}). Brier / log loss reward calibrated probabilities; "
               "MAE is the typical error in predicted delay minutes. Delays are heavy-tailed — modest, honest gains, not a crystal ball.")
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
        "- **Departures only, no arrivals, no ADS-B in the model.** The single strongest real-world predictor — the inbound aircraft running late — "
        "is not a feature yet (the live map shows ADS-B but does not feed the model).\n"
        "- **Rolling 91-day window, one season.** The data.gov.hk API keeps ~91 days; the training set (May–Aug 2026) has one typhoon "
        "(Noul, 25–26 Jul) in the validation split, so typhoon effects are learned from a handful of days and unconfirmed on test.\n"
        "- **Survivorship / churn.** Cancelled flights are excluded from the delay label; the schedule for tomorrow can still change.\n"
        "- **Staleness.** Predictions come from a 30-min cron; between runs they can be up to 30 min old (see 'data as of').")
