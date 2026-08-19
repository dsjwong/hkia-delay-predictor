"""Delay patterns over the rolling 91-day window: heatmap, ranked airlines / destinations, small multiples, daily bars."""
from __future__ import annotations

import streamlit as st

import charts as C
import data as D


def render() -> None:
    h = D.history()
    if h.empty:
        st.info("No departed flights in the window yet.")
        return
    st.markdown("### Delay patterns — last 91 days")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Departed flights", f"{len(h):,}", f"{h['date'].min()} → {h['date'].max()}", delta_color="off")
    k2.metric("Mean delay", f"{h['delay_min'].mean():.1f} min", f"median {h['delay_min'].median():.0f} min", delta_color="off")
    k3.metric("Delayed > 15 min", f"{h['delayed15'].mean():.0%}", "share of departures", delta_color="off")
    k4.metric("Airlines", f"{h['airline'].nunique()}", f"{h['dest1'].nunique()} destinations", delta_color="off")
    st.caption("Rolling window kept by the data.gov.hk API; delays clipped to [-60, 600] min like the training set; cancelled flights excluded.")

    metric = st.radio("Heatmap metric", ["Mean delay (min)", "% delayed > 15 min"], horizontal=True, label_visibility="collapsed")
    is_mean = metric.startswith("Mean")
    grid = h.pivot_table(index="dow", columns="hour", values="delay_min" if is_mean else "delayed15", aggfunc="mean")
    grid = grid.reindex(index=range(7), columns=range(24))
    st.plotly_chart(C.heatmap(grid, is_mean), width="stretch")

    c1, c2 = st.columns(2)
    a = h.groupby("airline").agg(n=("delay_min", "size"), mean_delay=("delay_min", "mean"), pct15=("delayed15", "mean")).reset_index()
    a = a[a["n"] >= 50].sort_values("pct15", ascending=False).head(15)
    a["label"] = a["airline"].map(lambda c: f"{D.airline_name(c)} ({c})")
    c1.plotly_chart(C.ranked_hbar(a, "label", "pct15", "n", "Airlines — share delayed > 15 min (top 15, n ≥ 50)", ".0%", "share > 15 min"),
                    width="stretch")
    d = h.groupby("dest1").agg(n=("delay_min", "size"), mean_delay=("delay_min", "mean"), pct15=("delayed15", "mean")).reset_index()
    d = d.sort_values("n", ascending=False).head(15)
    c2.plotly_chart(C.ranked_hbar(d, "dest1", "mean_delay", "n", "Top 15 destinations by flights — mean delay", ".0f", "mean delay (min)"),
                    width="stretch")
    with st.expander("Tables — every airline (n ≥ 50) and the top 25 destinations"):
        e1, e2 = st.columns(2)
        aa = h.groupby("airline").agg(n=("delay_min", "size"), mean_delay=("delay_min", "mean"), pct15=("delayed15", "mean")).reset_index()
        aa = aa[aa["n"] >= 50].sort_values("pct15", ascending=False)
        aa.insert(1, "name", aa["airline"].map(D.airline_name))
        e1.dataframe(aa.rename(columns={"airline": "code", "mean_delay": "mean delay (min)", "pct15": "% > 15 min"}), hide_index=True, width="stretch",
                     column_config={"mean delay (min)": st.column_config.NumberColumn(format="%.1f"),
                                    "% > 15 min": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
        dd = h.groupby("dest1").agg(n=("delay_min", "size"), mean_delay=("delay_min", "mean"), pct15=("delayed15", "mean")).reset_index()
        dd = dd.sort_values("n", ascending=False).head(25)
        e2.dataframe(dd.rename(columns={"dest1": "IATA", "mean_delay": "mean delay (min)", "pct15": "% > 15 min"}), hide_index=True, width="stretch",
                     column_config={"mean delay (min)": st.column_config.NumberColumn(format="%.1f"),
                                    "% > 15 min": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})

    top4 = h.groupby("airline").size().sort_values(ascending=False).head(4).index.tolist()
    st.plotly_chart(C.small_multiples_by_hour(h, top4, D.AIRLINE_NAMES), width="stretch")

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
    st.plotly_chart(C.daily_bars(daily), width="stretch")
