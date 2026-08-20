"""Plotly chart builders for the dashboard. All use the shared `hkia_zinc` template (app/theme.py).

Forms follow the dataviz skill: magnitude -> bars / heatmap (one hue), identity -> fixed categorical slots with a legend,
emphasis -> accent + grey, reliability -> line vs diagonal. Tooltips on every mark; no dual axes; thin marks.
Colour meaning: amber = the model / P(delay > 15); zinc = observed / neutral single-series magnitude.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import theme as T

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
BAR = dict(marker_line_width=0)


# ------------------------------------------------------------------ today
def today_timeline(df: pd.DataFrame) -> go.Figure:
    """Strip of flights by scheduled time (x) vs P(delay > 15) (y); departed vs pending as two categorical series."""
    d = df[df["p_delay15"].notna() & (df["status"] != "cancelled")].copy()
    fig = go.Figure()
    for status, color, name in (("scheduled", T.AMBER, "not yet departed"), ("departed", T.NEUTRAL, "departed")):
        s = d[d["status"] == status]
        if s.empty:
            continue
        delay = s["delay_min"].map(lambda v: "—" if pd.isna(v) else f"{v:+.0f} min actual")
        custom = np.stack([s["flight_no"], s["destination"].fillna(""), s["pred_delay_min"].fillna(np.nan), delay,
                           s["actual_time"].fillna("—")], axis=1)
        fig.add_scatter(
            x=s["sched_hkt"], y=s["p_delay15"], mode="markers", name=name,
            marker=dict(color=color, size=8, opacity=0.9, line=dict(color=T.SURFACE_2, width=2)),
            customdata=custom,
            hovertemplate="<b>%{customdata[0]}</b> → %{customdata[1]}<br>sched %{x|%H:%M} · actual %{customdata[4]}"
                          "<br>P(delay > 15) = %{y:.0%} · pred %{customdata[2]:.0f} min · %{customdata[3]}<extra></extra>")
    fig.add_hline(y=0.5, line=dict(color=T.BORDER_2, width=1))
    fig.update_layout(title="Flights through the day — P(delay > 15 min) by scheduled time",
                      yaxis=dict(tickformat=".0%", range=[0, 1], title="P(delay > 15)"),
                      xaxis=dict(tickformat="%H:%M", title="scheduled (HKT)"), hovermode="closest")
    return T.finish(fig, 330)


def hourly_pred_vs_obs(byh: pd.DataFrame) -> go.Figure:
    """Grouped bars per scheduled hour: predicted mean P vs observed late share (two series, legend)."""
    fig = go.Figure()
    fig.add_bar(x=byh["sched_hour"], y=byh["p"], name="predicted mean P(delay > 15)", marker_color=T.AMBER, customdata=byh["n"],
                hovertemplate="%{x:02d}:00 · predicted %{y:.0%} · %{customdata} flights<extra></extra>", **BAR)
    fig.add_bar(x=byh["sched_hour"], y=byh["obs"], name="observed share > 15 min (departed)", marker_color=T.NEUTRAL,
                customdata=byh["n_dep"], hovertemplate="%{x:02d}:00 · observed %{y:.0%} · %{customdata} departed<extra></extra>", **BAR)
    fig.update_layout(title="By scheduled hour — predicted vs observed late share", barmode="group", bargap=0.35, bargroupgap=0.08,
                      yaxis=dict(tickformat=".0%", range=[0, 1]), xaxis=dict(dtick=1, title="hour (HKT)"))
    return T.finish(fig, 300)


# ------------------------------------------------------------------ patterns
def heatmap(grid: pd.DataFrame, metric_is_mean: bool) -> go.Figure:
    z = grid.to_numpy()
    zmax = float(np.nanpercentile(z, 97)) if np.isfinite(z).any() else None  # one outlier cell must not flatten the ramp
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"{hh:02d}" for hh in range(24)], y=DOW, colorscale=T.zinc_scale(), xgap=2, ygap=2, zmin=0, zmax=zmax,
        colorbar=dict(title="min" if metric_is_mean else "", tickformat="" if metric_is_mean else ".0%", thickness=10, outlinewidth=0),
        hovertemplate=("%{y} %{x}:00 · %{z:.1f} min<extra></extra>" if metric_is_mean else "%{y} %{x}:00 · %{z:.0%}<extra></extra>")))
    fig.update_layout(title=("Mean delay (min)" if metric_is_mean else "Share delayed > 15 min") + " by scheduled hour (HKT) × weekday",
                      xaxis=dict(title="hour", showgrid=False), yaxis=dict(autorange="reversed", showgrid=False))
    return T.finish(fig, 340)


def ranked_hbar(df: pd.DataFrame, label_col: str, value_col: str, n_col: str, title: str, value_fmt: str = ".0%",
                value_title: str = "", height: int = 420) -> go.Figure:
    """Horizontal bars, one nominal series (neutral zinc — magnitude, not identity), n shown as a direct label at the bar end."""
    d = df.sort_values(value_col, ascending=True)
    txt = [f"n={int(n):,}" for n in d[n_col]]
    fig = go.Figure(go.Bar(
        x=d[value_col], y=d[label_col], orientation="h", marker_color=T.NEUTRAL, text=txt, textposition="outside",
        textfont=dict(color=T.MUTED, size=10), cliponaxis=False, customdata=d[n_col],
        hovertemplate="<b>%{y}</b> · %{x:" + value_fmt + "} · n=%{customdata:,}<extra></extra>", **BAR))
    fig.update_layout(title=title, bargap=0.35, xaxis=dict(tickformat=value_fmt, title=value_title, showgrid=True, gridcolor=T.GRID),
                      yaxis=dict(showgrid=False, tickfont=dict(size=11, color=T.INK_2)), margin=dict(r=50))
    return T.finish(fig, height)


def small_multiples_by_hour(h: pd.DataFrame, airlines: list[str], names: dict[str, str]) -> go.Figure:
    """2×2 small multiples: share delayed > 15 min by scheduled hour, one airline per facet, same hue (magnitude, not identity)."""
    fig = make_subplots(rows=2, cols=2, subplot_titles=[f"{names.get(a, a)} ({a})" for a in airlines], shared_yaxes=True,
                        horizontal_spacing=0.06, vertical_spacing=0.22)
    for i, a in enumerate(airlines):
        s = h[h["airline"] == a].groupby("hour").agg(p=("delayed15", "mean"), n=("delayed15", "size")).reindex(range(24))
        fig.add_bar(x=list(range(24)), y=s["p"], marker_color=T.NEUTRAL, customdata=s["n"], name=a, showlegend=False,
                    hovertemplate="%{x:02d}:00 · %{y:.0%} · n=%{customdata}<extra>" + a + "</extra>", **BAR,
                    row=i // 2 + 1, col=i % 2 + 1)
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    fig.update_xaxes(dtick=6)
    fig.update_annotations(font=dict(size=12, color=T.INK_2))
    fig.update_layout(title="Share delayed > 15 min by hour — top 4 airlines", bargap=0.3, margin=dict(t=80))
    return T.finish(fig, 420)


def daily_bars(daily: pd.DataFrame) -> go.Figure:
    """Mean delay per day; TC-signal days as a second (emphasis) series so a legend names them."""
    sig = daily.get("signal", pd.Series(0, index=daily.index)).fillna(0)
    fig = go.Figure()
    no = daily[sig == 0]
    fig.add_bar(x=no["date"], y=no["mean_delay"], name="normal day", marker_color=T.NEUTRAL,
                hovertemplate="%{x} · %{y:.0f} min<extra></extra>", **BAR)
    tc = daily[sig > 0]
    if not tc.empty:
        fig.add_bar(x=tc["date"], y=tc["mean_delay"], name="TC signal in force", marker_color=T.AMBER,
                    customdata=np.stack([tc["signal"], tc["tc_name"].fillna("")], axis=1),
                    hovertemplate="%{x} · %{y:.0f} min · signal %{customdata[0]} %{customdata[1]}<extra></extra>", **BAR)
    fig.update_layout(title="Mean departure delay per day", yaxis_title="min", barmode="overlay", bargap=0.3)
    return T.finish(fig, 280)


# ------------------------------------------------------------------ model
def reliability(cal: pd.DataFrame, label: str = "XGBoost (test)", title: str = "Reliability diagram (marker size ~ bin count)",
                min_n: int = 0) -> go.Figure:
    """Bins with fewer than `min_n` flights are drawn hollow and the connecting line skips them: joining a 6-flight bin
    to its neighbours turns three coin flips into a dramatic-looking zig-zag."""
    thin = (cal["n"] < min_n).to_numpy() if min_n else np.zeros(len(cal), dtype=bool)
    fig = go.Figure()
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=T.GREY, width=1), name="perfect calibration", hoverinfo="skip")
    fig.add_scatter(x=cal["pred_mean"], y=np.where(thin, np.nan, cal["obs_rate"]), mode="lines", name=label,
                    line=dict(color=T.AMBER, width=1.5), connectgaps=False, hoverinfo="skip", showlegend=True)
    size = np.clip(np.sqrt(cal["n"]) * 0.6, 7, 24)
    hov = "predicted %{x:.2f} · observed %{y:.2f} · n=%{customdata:,}<extra></extra>"
    fig.add_scatter(x=cal["pred_mean"][~thin], y=cal["obs_rate"][~thin], mode="markers", name=label, showlegend=False,
                    marker=dict(size=size[~thin], color=T.AMBER, line=dict(color=T.SURFACE_2, width=2)),
                    customdata=cal["n"][~thin], hovertemplate=hov)
    if thin.any():   # hollow, and its own trace so the legend swatch is hollow too
        fig.add_scatter(x=cal["pred_mean"][thin], y=cal["obs_rate"][thin], mode="markers", name=f"under {min_n} flights",
                        marker=dict(size=size[thin], color=T.SURFACE_2, line=dict(color=T.AMBER, width=2)),
                        customdata=cal["n"][thin], hovertemplate=hov)
    fig.update_layout(title=title, xaxis=dict(title="mean predicted P(delay > 15)", range=[0, 1], showgrid=True, gridcolor=T.GRID),
                      yaxis=dict(title="observed rate", range=[0, 1]))
    return T.finish(fig, 380)


# ------------------------------------------------------------------ live report card
def _auc_axis(values: list) -> tuple[list[float], list[float]]:
    """Round-tenth y range that always keeps the 0.5 coin-flip line in view without squashing a 0.58 -> 0.71 spread."""
    v = [x for x in values if x is not None and x == x]
    lo = np.floor(min([0.45, *v]) * 10) / 10
    hi = np.ceil(max([0.8, *v]) * 10) / 10
    ticks = [round(t, 1) for t in np.arange(lo, hi + 1e-9, 0.1)]
    return [max(0.0, lo), min(1.0, hi)], ticks


def live_daily_auc(daily: pd.DataFrame) -> go.Figure:
    """AUC per HKT departure date, model vs airline x hour baseline, with the coin-flip reference line.

    A day whose flights were all on time (or all late) has no AUC: the point is missing, never faked as 0.5.
    """
    fig = go.Figure()
    has_b = "baseline_auc" in daily and daily["baseline_auc"].notna().any()
    rng, ticks = _auc_axis(list(daily["model_auc"]) + (list(daily["baseline_auc"]) if has_b else []))
    fig.add_hline(y=0.5, line=dict(color=T.GREY, width=1), annotation_text="coin flip", annotation_position="bottom right",
                  annotation=dict(font=dict(size=10, color=T.MUTED)))
    cd = np.stack([daily["n"], daily["delayed15_rate"], daily["model_mae"]], axis=1)
    fig.add_scatter(x=daily["date"], y=daily["model_auc"], mode="lines+markers", name="model (XGBoost, live)",
                    line=dict(color=T.AMBER, width=1.5), marker=dict(color=T.AMBER, size=7), customdata=cd,
                    hovertemplate="%{x} · AUC %{y:.3f}<br>n=%{customdata[0]} · %{customdata[1]:.0%} late · MAE %{customdata[2]:.1f} min<extra></extra>")
    if has_b:
        fig.add_scatter(x=daily["date"], y=daily["baseline_auc"], mode="lines+markers", name="airline × hour baseline",
                        line=dict(color=T.TEAL, width=1.5), marker=dict(color=T.TEAL, size=7),
                        hovertemplate="%{x} · AUC %{y:.3f}<extra>baseline</extra>")
    fig.update_layout(title="AUC per day — model vs baseline", yaxis=dict(range=rng, tickvals=ticks, tickformat=".1f"),
                      xaxis=dict(title="HKT departure date", type="category"), hovermode="x unified")
    return T.finish(fig, 300)


def lead_bucket_bars(buckets: pd.DataFrame) -> go.Figure:
    """AUC by how far ahead of the actual departure the last score was written. Bars from 0, coin flip marked."""
    fig = go.Figure()
    has_b = "baseline_auc" in buckets and buckets["baseline_auc"].notna().any()
    lbl = [f"{r.label}<br><span style='font-size:10px'>n={int(r.n)}{' · thin' if r.thin else ''}</span>" for r in buckets.itertuples(index=False)]
    fig.add_bar(x=lbl, y=buckets["model_auc"], name="model (XGBoost, live)", marker_color=T.AMBER, customdata=buckets["n"],
                hovertemplate="AUC %{y:.3f} · n=%{customdata}<extra>model</extra>", **BAR)
    if has_b:
        fig.add_bar(x=lbl, y=buckets["baseline_auc"], name="airline × hour baseline", marker_color=T.TEAL, customdata=buckets["n"],
                    hovertemplate="AUC %{y:.3f} · n=%{customdata}<extra>baseline</extra>", **BAR)
    fig.add_hline(y=0.5, line=dict(color=T.GREY, width=1), annotation_text="coin flip", annotation_position="top right",
                  annotation=dict(font=dict(size=10, color=T.MUTED)))
    fig.update_layout(title="AUC by forecast horizon (score → scheduled departure)", barmode="group", bargap=0.4, bargroupgap=0.08,
                      yaxis=dict(range=[0, 1], tickformat=".2f"), xaxis=dict(title=""))
    return T.finish(fig, 300)


def importance_hbar(imp: pd.Series, title: str) -> go.Figure:
    fig = go.Figure(go.Bar(x=imp.values, y=imp.index, orientation="h", marker_color=T.NEUTRAL,
                           hovertemplate="%{y}: gain %{x:.1f}<extra></extra>", **BAR))
    fig.update_layout(title=title, bargap=0.35, xaxis=dict(title="gain", showgrid=True, gridcolor=T.GRID),
                      yaxis=dict(showgrid=False, tickfont=dict(size=11, color=T.INK_2)), margin=dict(b=40))
    return T.finish(fig, 400)
