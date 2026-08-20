"""Case study — Typhoon Noul at HKIA, 24-26 Jul 2026. Streamlit twin of the React /typhoon route.

Reads the committed static artefact `web/public/data/case_noul.json` (written once by `python -m hkia.case_study`), so
both front ends show the same numbers and this page needs neither xgboost nor the analysis at runtime.

Honesty rule, same as the React page: live scoring began 2026-08-17, so nothing here was ever predicted live. The model
half is IN-SAMPLE (24-26 Jul sits in the validation split) and says so in the UI — a callout above it and "in-sample" in
the section heading, chart title and table caption — not only in the prose.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import charts as C
import data as D
import theme as T


def _hourly(c: dict) -> pd.DataFrame:
    h = pd.DataFrame(c["hourly"])
    h["t"] = pd.to_datetime(h["t"])
    return h


def _hm(ts: str | None, fmt: str = "%d %b %H:%M") -> str:
    return "—" if not ts else pd.Timestamp(ts).strftime(fmt)


def _sig(s: int) -> str:
    return f"T{s}" if s else "none"


def render() -> None:
    c = D.case_study()
    if not c:
        st.info(f"Case study artefact not found at `{D.CASE_JSON}`. Generate it once with "
                "`python -m hkia.case_study` and commit it — it is static history, not cron output.")
        return

    h, hd, base, rec = _hourly(c), c["headline"], c["baseline"], c["recovery"]
    r = c.get("retrospective")

    T.badges(T.badge(f"signal <b>{c['episode']['sequence']}</b>", "warn"),
             T.badge(f"window <b>{c['window']['days'][0]} → {c['window']['days'][-1]}</b>"),
             T.badge("static snapshot · <b>python -m hkia.case_study</b>"))

    st.warning("**No prediction was published for these flights — this is a data story, not a live forecast.** "
               f"Live scoring began **{(r or {}).get('live_scoring_began', '2026-08-17')}**, three weeks after Noul. "
               "The model numbers below come from re-running the shipped model over these flights after the fact, with "
               + (f"the same feature builder — and 24–26 Jul falls inside its **validation split** "
                  f"({r['val_dates'][0]} → {r['val_dates'][1]}), which was used for early stopping and model selection. "
                  if r else "the same feature builder. ")
               + "They are **in-sample**: an illustration of what the model says about these hours, never a measurement "
                 "of skill.")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Peak signal", f"No. {hd['peak_signal']}", c["episode"]["sequence"], delta_color="off")
    k2.metric("Departures cancelled", f"{hd['n_cancelled_episode']:,}",
              f"{hd['cancel_rate_episode']:.1%} of {hd['n_flights_episode']:,} on the 3 signal days", delta_color="off")
    k3.metric("Peak hourly mean delay", f"{hd['peak_hour_mean_delay']:.0f} min",
              f"{_hm(hd['peak_hour'])} HKT · {hd['peak_hour_n']} flights", delta_color="off")
    k4.metric("Hours to recover", "—" if hd["hours_to_recover"] is None else f"{hd['hours_to_recover']:.0f} h",
              f"after the all-clear, back to {base['mean_delay']:.1f} min", delta_color="off")

    st.plotly_chart(C.case_hourly_delay(h), width="stretch")
    st.caption("One y-axis — minutes. The typhoon signal is a labelled background band (T1 / T3 / T8 / T9), not a "
               f"second scale. Delays outside [{c['clip']['min']}, {c['clip']['max']}] min are excluded from every "
               "average, as everywhere else in this app; cancelled flights have no delay label at all and appear only "
               "in the strip below.")

    c1, c2 = st.columns(2)
    c1.plotly_chart(C.case_wind(h), width="stretch")
    c2.plotly_chart(C.case_cancellations(h), width="stretch")

    # ---------------------------------------------------------------- the story, condensed
    st.markdown("#### What happened")
    by = {row["signal"]: row for row in c["by_signal"]}
    t8 = next((x for x in (r or {}).get("by_signal", []) if x["signal"] == 8), None)
    worst = c["worst_flights"][0] if c["worst_flights"] else None
    cpa = c["cancellations"]["by_airline"][0] if c["cancellations"]["by_airline"] else None
    st.markdown(
        f"The Observatory hoisted the No. 1 standby signal at **{_hm(c['episode']['first_signal'])} HKT** and walked it "
        f"up through **{c['episode']['sequence']}**, with the hurricane-force No. 9 standing overnight, before the "
        f"all-clear at **{_hm(rec['all_clear_ts'])} HKT**. Peak gust **{hd['peak_gust_kt']:.0f} kt**, visibility down to "
        f"**{hd['min_visib_sm']:.1f} statute miles**.\n\n"
        f"The airport did not degrade gradually — it fell off a cliff at signal 8. With no signal in force it cancels "
        f"**{base['cancel_rate']:.1%}** of departures and averages **{base['mean_delay']:.1f} min** of delay; under "
        f"signal 3 the cancellation rate is **{by[3]['cancel_rate']:.0%}**, under signal 8 it is "
        f"**{by[8]['cancel_rate']:.0%}** and the flights that do leave average **{by[8]['mean_delay']:.0f} min** late. "
        f"The worst hour, **{_hm(hd['peak_hour'])} HKT**, averaged **{hd['peak_hour_mean_delay']:.0f} min** over "
        f"{hd['peak_hour_n']} departures. Over the three signal days **{hd['n_cancelled_episode']:,}** of "
        f"{hd['n_flights_episode']:,} scheduled departures were cancelled"
        + (f", {cpa['n_cancelled']} of them {cpa['name']}'s" if cpa else "")
        + f"; {hd['n_hours_no_departures']} clock hours saw no departure at all.\n\n"
        f"Recovery lagged the storm: the signal came down at **{_hm(rec['all_clear_ts'])} HKT** but hourly mean delay "
        f"only returned to the no-signal baseline of {base['mean_delay']:.1f} min at "
        f"**{_hm(rec['recovered_at'])} HKT** — **{rec['hours_to_recover']:.0f} hours later**. The tail is worse than the "
        f"mean: the ten longest delays all ran past the {c['clip']['max']}-minute clip"
        + (f", up to **{worst['delay_min']:,.0f} minutes**" if worst else "") + ".\n\n"
        + (f"Re-scored after the fact the model *ranks* these flights well — AUC **{r['overall']['auc']:.3f}** over "
           f"{r['overall']['n']:,} departures, flagging {r['overall']['pct_flagged']:.0%} above "
           f"P = {r['flag_threshold']} against an observed late rate of {r['overall']['obs_rate']:.0%} — but it badly "
           f"under-calls the magnitude: under signal 8 it expected **{t8['mean_pred_delay']:.0f} min** where the airport "
           f"ran **{t8['mean_obs_delay']:.0f} min** late. Nothing in the feature set says \"the airport has stopped\".\n\n"
           if r and t8 else "")
        + f"Caveats over numbers: {'every model figure here is in-sample, ' if r else ''}one typhoon is one event "
          f"({by[8]['n']} flights under signal 8, {by[9]['n']} under signal 9 — an anecdote, not a measured effect), and "
          f"every average is conditioned on the flight having eventually left.")

    # ---------------------------------------------------------------- tables
    st.markdown("#### Totals by signal level")
    tot = pd.DataFrame(c["by_signal"])
    tot["signal"] = tot["signal"].map(_sig)
    tot = pd.concat([tot, pd.DataFrame([{**base, "signal": "baseline"}])], ignore_index=True)
    tot["cancel_rate"] = tot["cancel_rate"] * 100   # NumberColumn formats the raw value, so a fraction would read 0.0%
    st.dataframe(tot[["signal", "n", "n_cancelled", "cancel_rate", "mean_delay", "p90_delay", "pct15"]]
                 .rename(columns={"signal": "signal", "n": "flights", "n_cancelled": "cancelled",
                                  "cancel_rate": "cancel rate", "mean_delay": "mean delay (min)",
                                  "p90_delay": "p90 (min)", "pct15": "% > 15 min"}),
                 hide_index=True, width="stretch",
                 column_config={"mean delay (min)": st.column_config.NumberColumn(format="%.1f"),
                                "p90 (min)": st.column_config.NumberColumn(format="%.0f"),
                                "cancel rate": st.column_config.NumberColumn(format="%.1f%%"),
                                "% > 15 min": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
    st.caption("Signal rows are the case-study window only, so the `none` row is mostly the recovery hours after the "
               "all-clear; the baseline row is every departure in the database with no signal in force "
               f"({base['n_days']} days, {base['date_min']} → {base['date_max']}).")

    st.markdown("#### The ten longest delays")
    w = pd.DataFrame(c["worst_flights"])
    w["scheduled (HKT)"] = w["sched_ts"].map(lambda x: _hm(x, "%d %b %H:%M"))
    w["actual (HKT)"] = w["actual_ts"].map(lambda x: _hm(x, "%d %b %H:%M"))
    w["to"] = w["dest_city"] + " (" + w["dest"] + ")"
    w["signal"] = w["signal"].map(_sig)
    st.dataframe(w[["flight_no", "airline_name", "to", "scheduled (HKT)", "actual (HKT)", "delay_min", "signal"]]
                 .rename(columns={"flight_no": "flight", "airline_name": "airline", "delay_min": "delay (min)"}),
                 hide_index=True, width="stretch",
                 column_config={"delay (min)": st.column_config.NumberColumn(format="%.0f")})
    st.caption(f"Uncapped: every one of these is past the {c['clip']['max']}-minute clip and is therefore excluded from "
               "the averages above.")

    with st.expander("Who lost flights — cancellation clusters"):
        ca = pd.DataFrame(c["cancellations"]["by_airline"])
        st.dataframe(ca.rename(columns={"airline": "code", "n_cancelled": "cancelled", "n_sched": "scheduled"}),
                     hide_index=True, width="stretch",
                     column_config={"rate": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
        st.caption("Worst-hit destinations: "
                   + " · ".join(f"{d['city']} ({d['dest']}) {d['n_cancelled']}" for d in c["cancellations"]["by_dest"]))

    # ---------------------------------------------------------------- retrospective (in-sample)
    if r:
        st.markdown("#### Model retrospective — in-sample, illustration only")
        T.badges(T.badge("<b>in-sample</b> — not a skill measurement", "warn"),
                 T.badge(f"model <b>{r['model_version']}</b>"),
                 T.badge(f"validation split <b>{r['val_dates'][0]} → {r['val_dates'][1]}</b>"))
        rows = pd.DataFrame(r["by_signal"])
        rows["label"] = rows["signal"].map(_sig)
        st.plotly_chart(C.case_pred_vs_obs(rows), width="stretch")
        tbl = pd.concat([pd.DataFrame([{**r["overall"], "signal": "all"}]),
                         pd.DataFrame(r["by_signal"]).assign(signal=lambda d: d["signal"].map(_sig))],
                        ignore_index=True)
        for col in ("obs_rate", "pct_flagged"):     # same reason: percent columns are stored as fractions
            tbl[col] = tbl[col] * 100
        st.dataframe(tbl[["signal", "n", "obs_rate", "pct_flagged", "auc", "brier", "mean_pred_delay", "mean_obs_delay"]]
                     .rename(columns={"obs_rate": "observed > 15 min", "pct_flagged": f"flagged P > {r['flag_threshold']}",
                                      "mean_pred_delay": "predicted delay (min)", "mean_obs_delay": "observed delay (min)"}),
                     hide_index=True, width="stretch",
                     column_config={"auc": st.column_config.NumberColumn(format="%.3f"),
                                    "brier": st.column_config.NumberColumn(format="%.3f"),
                                    "predicted delay (min)": st.column_config.NumberColumn(format="%.0f"),
                                    "observed delay (min)": st.column_config.NumberColumn(format="%.0f"),
                                    "observed > 15 min": st.column_config.NumberColumn(format="%.0f%%"),
                                    f"flagged P > {r['flag_threshold']}": st.column_config.NumberColumn(format="%.0f%%")})
        st.caption(r["note"] + " Read the last two columns together: the ranking holds up, the magnitude does not. "
                               "Slices with a handful of flights (signal 9) are noise — the AUC there is a coin flip.")

    others = ", ".join(f"Typhoon {e['name']} (peak No. {e['peak_signal']}, {e['start'][:10]} → {e['end'][:10]})"
                       for e in c.get("other_episodes", []))
    msn = c.get("other_monsoon")
    if others or msn:
        st.info("**Noul was not the only weather in the window.** The data also covers "
                + others
                + ((" and " if others else "") + f"{msn['n']} strong-monsoon episodes "
                   f"({msn['date_min']} → {msn['date_max']})" if msn else "")
                + ". None went past a No. 1 standby signal, so none of them shut the airport — Noul is the only episode "
                  "in this dataset with a signal 8 or above.")

    st.caption(f"{c['clip']['note']}. Sources: {' · '.join(c['sources'].values())}. "
               f"Generated {_hm(c['generated_at'], '%d %b %Y %H:%M')} HKT by `{c['regenerate']}` — a one-off artefact, "
               "not cron output.")
