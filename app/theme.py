"""Dark ops/radar look for the dashboard: palette tokens, CSS, one shared plotly template, small HTML helpers.

Palette validated with the dataviz skill's validate_palette.js against surface #0b1220 (dark):
  categorical  #3987e5 #d95926 #199e70 #c98500  -> adjacent: ALL PASS (worst CVD dE 8.4, normal 19.8); first 3 all-pairs: PASS
  P(delay) ramp (amber, ordinal, dim -> bright) #6b4608 #94620a #bd7f0c #e39d14 #ffbf3d -> PASS (light-end 2.23:1)
  heatmap ramp (blue)  #184f95 #256abf #3987e5 #6da7ec #9ec5f4 -> PASS
  status (reserved, never a series): good #0ca30c, warning #fab219, critical #d03b3b
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# -- surfaces & ink
SURFACE = "#0b1220"
SURFACE_2 = "#121c2e"
BORDER = "rgba(255,255,255,0.08)"
INK = "#e6ebf2"
INK_2 = "#b4bdcc"
MUTED = "#8a94a6"
GRID = "#1c2739"

# -- categorical (fixed order, never cycled)
BLUE, ORANGE, AQUA, YELLOW = "#3987e5", "#d95926", "#199e70", "#c98500"
CATEGORICAL = [BLUE, ORANGE, AQUA, YELLOW]
GREY = "#5b6577"          # de-emphasis
# -- sequential ramps (one hue each; on the dark surface low = dim, high = bright)
AMBER_RAMP = ["#6b4608", "#94620a", "#bd7f0c", "#e39d14", "#ffbf3d"]      # P(delay > 15)
BLUE_RAMP = ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4"]       # heatmap magnitude
# -- status (reserved)
GOOD, WARNING, CRITICAL = "#0ca30c", "#fab219", "#d03b3b"

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
MONO = "'SF Mono', SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"


def amber_scale() -> list[list]:
    n = len(AMBER_RAMP) - 1
    return [[i / n, c] for i, c in enumerate(AMBER_RAMP)]


def blue_scale() -> list[list]:
    n = len(BLUE_RAMP) - 1
    return [[i / n, c] for i, c in enumerate(BLUE_RAMP)]


def amber_rgb(p: float) -> tuple[int, int, int]:
    """Interpolate the amber ramp at p in [0,1] -> (r,g,b) for pydeck."""
    p = 0.0 if p is None or p != p else min(max(float(p), 0.0), 1.0)
    pos = p * (len(AMBER_RAMP) - 1)
    i = min(int(pos), len(AMBER_RAMP) - 2)
    f = pos - i
    a, b = AMBER_RAMP[i].lstrip("#"), AMBER_RAMP[i + 1].lstrip("#")
    ra, ga, ba = int(a[0:2], 16), int(a[2:4], 16), int(a[4:6], 16)
    rb, gb, bb = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
    return (round(ra + (rb - ra) * f), round(ga + (gb - ga) * f), round(ba + (bb - ba) * f))


def register_template() -> None:
    """Register and activate the shared plotly template once per process."""
    if "hkia_dark" in pio.templates:
        pio.templates.default = "hkia_dark"
        return
    t = go.layout.Template(pio.templates["plotly_dark"])
    t.layout.update(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=INK_2),
        title=dict(font=dict(size=14, color=INK), x=0, xanchor="left", yref="container", y=0.985, yanchor="top"),
        colorway=CATEGORICAL,
        margin=dict(l=8, r=8, t=66, b=8),
        hoverlabel=dict(bgcolor=SURFACE_2, bordercolor=BORDER, font=dict(family=FONT, size=12, color=INK)),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=11, color=INK_2)),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=GRID, tickcolor=GRID, title=dict(font=dict(size=11, color=MUTED)),
                   tickfont=dict(size=11, color=MUTED)),
        yaxis=dict(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False, linecolor="rgba(0,0,0,0)",
                   title=dict(font=dict(size=11, color=MUTED)), tickfont=dict(size=11, color=MUTED)),
        coloraxis=dict(colorbar=dict(outlinewidth=0, thickness=10, len=0.8, tickfont=dict(size=10, color=MUTED))),
    )
    pio.templates["hkia_dark"] = t
    pio.templates.default = "hkia_dark"


def finish(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(template="hkia_dark", height=height)
    return fig


CSS = f"""
<style>
:root {{ --hk-surface:{SURFACE}; --hk-surface2:{SURFACE_2}; --hk-border:{BORDER}; --hk-ink:{INK}; --hk-muted:{MUTED}; --hk-accent:{BLUE}; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 2rem; max-width: 1500px; }}
h1, h2, h3 {{ letter-spacing: -0.01em; }}
h1 {{ font-size: 1.55rem !important; padding-bottom: 0.2rem !important; }}
h4 {{ font-size: 0.95rem !important; color: {INK_2}; text-transform: uppercase; letter-spacing: 0.06em; padding-top: 0.6rem !important; }}
/* metric tiles as cards */
div[data-testid="stMetric"] {{
  background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 10px; padding: 10px 14px 8px 14px;
}}
div[data-testid="stMetric"] label p {{ font-size: 0.72rem !important; color: {MUTED} !important; text-transform: uppercase; letter-spacing: 0.06em; }}
div[data-testid="stMetricValue"] {{ font-family: {MONO}; font-size: 1.55rem !important; color: {INK}; font-variant-numeric: tabular-nums; }}
div[data-testid="stMetricDelta"] {{ font-size: 0.78rem !important; color: {INK_2} !important; }}
div[data-testid="stMetricDelta"] svg {{ display: none; }}
/* header bar */
.hk-header {{ display:flex; align-items:center; justify-content:space-between; gap: 12px; padding: 8px 14px; margin-bottom: 10px;
  background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 10px; }}
.hk-header .title {{ font-weight: 650; font-size: 1.05rem; color: {INK}; letter-spacing: 0.01em; }}
.hk-header .sub {{ color: {MUTED}; font-size: 0.8rem; margin-left: 10px; font-weight: 400; }}
.hk-live {{ font-family: {MONO}; font-size: 0.78rem; color: {INK_2}; display:flex; align-items:center; gap: 8px; white-space: nowrap; }}
.hk-dot {{ width: 8px; height: 8px; border-radius: 50%; background: {GOOD}; box-shadow: 0 0 0 0 rgba(12,163,12,0.6); animation: hkpulse 2s infinite; }}
.hk-dot.off {{ background: {CRITICAL}; animation: none; }}
@keyframes hkpulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(12,163,12,0.55); }} 70% {{ box-shadow: 0 0 0 8px rgba(12,163,12,0); }} 100% {{ box-shadow: 0 0 0 0 rgba(12,163,12,0); }} }}
/* strips / badges */
.hk-strip {{ font-family: {MONO}; font-size: 0.78rem; color: {INK_2}; background: {SURFACE_2}; border: 1px solid {BORDER};
  border-radius: 8px; padding: 8px 12px; margin: 4px 0 8px 0; overflow-x: auto; white-space: nowrap; }}
.hk-badge {{ display:inline-block; font-size: 0.7rem; padding: 2px 8px; border-radius: 999px; border: 1px solid {BORDER}; color: {INK_2}; margin-right: 6px; }}
.hk-badge.warn {{ border-color: {WARNING}; color: {WARNING}; }}
.hk-badge.crit {{ border-color: {CRITICAL}; color: {CRITICAL}; }}
.hk-badge.ok {{ border-color: {GOOD}; color: {GOOD}; }}
/* sidebar */
section[data-testid="stSidebar"] {{ background: {SURFACE_2}; border-right: 1px solid {BORDER}; }}
section[data-testid="stSidebar"] .hk-brand {{ font-weight: 700; font-size: 1.05rem; color: {INK}; letter-spacing: 0.02em; }}
section[data-testid="stSidebar"] .hk-brand small {{ display:block; color: {MUTED}; font-weight: 400; font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; }}
div[data-testid="stRadio"] label p {{ font-size: 0.95rem; }}
/* tables & captions */
div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 8px; }}
div[data-testid="stCaptionContainer"] p {{ color: {MUTED}; }}
/* pydeck */
div[data-testid="stDeckGlJsonChart"] {{ border: 1px solid {BORDER}; border-radius: 10px; overflow: hidden; }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def header(title: str, subtitle: str = "", as_of: str = "", live: bool = True) -> None:
    dot = "hk-dot" if live else "hk-dot off"
    st.markdown(
        f'<div class="hk-header"><div><span class="title">{title}</span><span class="sub">{subtitle}</span></div>'
        f'<div class="hk-live"><span class="{dot}"></span>{"LIVE" if live else "STALE"} · {as_of}</div></div>',
        unsafe_allow_html=True)


def strip(text: str) -> None:
    st.markdown(f'<div class="hk-strip">{text}</div>', unsafe_allow_html=True)


def badge(text: str, kind: str = "") -> str:
    return f'<span class="hk-badge {kind}">{text}</span>'
