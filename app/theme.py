"""Neutral dark-grey design system for the dashboard (shadcn/ui "zinc" dark — Linear / Vercel dashboard look): tokens, CSS,
one shared plotly template, small HTML helpers. Tokens are mirrored in .streamlit/config.toml; docs/design.md explains them.

Palette validated with the dataviz skill's validate_palette.js against surface #09090b (dark):
  categorical  #c9820c #3d87e0 #14a88d #9b6fe0  -> adjacent ALL PASS (worst CVD dE 14.0, normal 17.4); first 3 all-pairs PASS
  P(delay) ramp (amber, ordinal, dim -> bright) #6b4608 #94620a #bd7f0c #e39d14 #ffbf3d -> PASS (light-end 2.37:1, hue spread 8 deg)
  magnitude ramp (zinc, ordinal)  #45454c #5e5e66 #7a7a83 #9c9ca4 #c4c4ca #ececef -> PASS
  status (reserved, never a series): good #22c55e, warning #f59e0b, critical #ef4444

Colour meaning: amber = P(delay > 15) / the model's prediction; zinc = observed / neutral / other traffic; green = live.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# -- surfaces & ink (zinc scale)
SURFACE = "#09090b"        # zinc-950  page
SURFACE_2 = "#18181b"      # zinc-900  cards, sidebar
SURFACE_3 = "#1f1f23"      # elevated (hover, code, tooltips)
BORDER = "#27272a"         # zinc-800  hairlines
BORDER_2 = "#3f3f46"       # zinc-700  hover / focus hairline
INK = "#fafafa"            # zinc-50   primary text
INK_2 = "#a1a1aa"          # zinc-400  secondary text, axis ticks
MUTED = "#71717a"          # zinc-500  captions, labels
GRID = BORDER

# -- the one accent
ACCENT = "#f59e0b"         # amber-500 — P(delay), primary emphasis in chrome
ACCENT_DIM = "#b45309"     # amber-700

# -- categorical (fixed order, never cycled). Slot 1 = the model / P(delay) series; slot 2 neutral blue only if a 2nd identity is needed.
AMBER, BLUE, TEAL, VIOLET = "#c9820c", "#3d87e0", "#14a88d", "#9b6fe0"
CATEGORICAL = [AMBER, BLUE, TEAL, VIOLET]
NEUTRAL = "#a1a1aa"        # zinc-400: the observed / single-series magnitude bar
GREY = "#52525b"           # zinc-600: de-emphasis, reference lines
# -- sequential ramps (one hue each; dim -> bright on the dark surface)
AMBER_RAMP = ["#6b4608", "#94620a", "#bd7f0c", "#e39d14", "#ffbf3d"]             # P(delay > 15)
ZINC_RAMP = ["#45454c", "#5e5e66", "#7a7a83", "#9c9ca4", "#c4c4ca", "#ececef"]   # heatmap magnitude
# -- status (reserved)
GOOD, WARNING, CRITICAL = "#22c55e", "#f59e0b", "#ef4444"

FONT = "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
MONO = "'SF Mono', SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
RADIUS = 12
SPACE = 8


def _scale(ramp: list[str]) -> list[list]:
    n = len(ramp) - 1
    return [[i / n, c] for i, c in enumerate(ramp)]


def amber_scale() -> list[list]:
    return _scale(AMBER_RAMP)


def zinc_scale() -> list[list]:
    return _scale(ZINC_RAMP)


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def ramp_rgb(ramp: list[str], p: float) -> tuple[int, int, int]:
    """Interpolate a hex ramp at p in [0,1] -> (r,g,b) for pydeck."""
    p = 0.0 if p is None or p != p else min(max(float(p), 0.0), 1.0)
    pos = p * (len(ramp) - 1)
    i = min(int(pos), len(ramp) - 2)
    f = pos - i
    a, b = _hex_rgb(ramp[i]), _hex_rgb(ramp[i + 1])
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))  # type: ignore[return-value]


def amber_rgb(p: float) -> tuple[int, int, int]:
    return ramp_rgb(AMBER_RAMP, p)


# ------------------------------------------------------------------ plotly
def register_template() -> None:
    """Register and activate the shared plotly template once per process."""
    if "hkia_zinc" in pio.templates:
        pio.templates.default = "hkia_zinc"
        return
    t = go.layout.Template(pio.templates["plotly_dark"])
    axis_font = dict(size=11, color=INK_2)
    t.layout.update(
        paper_bgcolor=SURFACE_2, plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=INK_2),
        title=dict(font=dict(family=FONT, size=13, color=INK, weight=500), x=0, xanchor="left", yref="container", y=0.985, yanchor="top"),
        colorway=CATEGORICAL,
        margin=dict(l=16, r=16, t=64, b=16),
        hoverlabel=dict(bgcolor=SURFACE_3, bordercolor=BORDER_2, font=dict(family=FONT, size=12, color=INK)),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=11, color=INK_2),
                    itemsizing="constant"),
        xaxis=dict(showgrid=False, zeroline=False, showline=False, linecolor=GRID, tickcolor="rgba(0,0,0,0)", ticks="",
                   title=dict(font=dict(size=11, color=MUTED), standoff=8), tickfont=axis_font, automargin=True),
        yaxis=dict(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False, showline=False, tickcolor="rgba(0,0,0,0)", ticks="",
                   title=dict(font=dict(size=11, color=MUTED), standoff=8), tickfont=axis_font, automargin=True),
        coloraxis=dict(colorbar=dict(outlinewidth=0, thickness=8, len=0.8, tickfont=dict(size=10, color=MUTED))),
        bargap=0.35,
    )
    t.data.bar = [go.Bar(marker=dict(line=dict(width=0)))]
    t.data.scatter = [go.Scatter(line=dict(width=1.5))]
    pio.templates["hkia_zinc"] = t
    pio.templates.default = "hkia_zinc"


def finish(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(template="hkia_zinc", height=height)
    return fig


# ------------------------------------------------------------------ css
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {{ --hk-surface:{SURFACE}; --hk-surface2:{SURFACE_2}; --hk-surface3:{SURFACE_3}; --hk-border:{BORDER}; --hk-ink:{INK};
  --hk-ink2:{INK_2}; --hk-muted:{MUTED}; --hk-accent:{ACCENT}; --hk-radius:{RADIUS}px; }}
html, body, [class*="css"], .stApp, .stMarkdown, p, li, label, input, button {{ font-family: {FONT} !important; letter-spacing: -0.006em; }}
.stApp {{ background: {SURFACE}; }}
code, pre, kbd, samp {{ font-family: {MONO} !important; }}
/* chrome: hide Streamlit's coloured header strip + deploy/menu buttons, keep the sidebar collapse control */
header[data-testid="stHeader"] {{ background: transparent; }}
div[data-testid="stDecoration"] {{ display: none; }}
div[data-testid="stToolbar"] {{ display: none; }}
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ padding: 2.4rem 2rem 2rem 2rem; max-width: 1500px; }}
/* type scale: 28/20/15/13/11 */
h1 {{ font-size: 1.5rem !important; font-weight: 600 !important; letter-spacing: -0.02em !important; color: {INK}; padding: 0 0 0.2rem 0 !important; }}
h2 {{ font-size: 1.2rem !important; font-weight: 600 !important; letter-spacing: -0.015em !important; padding-top: 0.4rem !important; }}
h3 {{ font-size: 1.05rem !important; font-weight: 600 !important; letter-spacing: -0.01em !important; padding: 0.8rem 0 0.2rem 0 !important; }}
h4 {{ font-size: 0.72rem !important; font-weight: 600 !important; color: {MUTED}; text-transform: uppercase; letter-spacing: 0.08em !important;
  padding: 1rem 0 0.2rem 0 !important; }}
p, li {{ color: {INK_2}; }}
strong {{ color: {INK}; font-weight: 600; }}
a, a:visited {{ color: {INK} !important; text-decoration: underline; text-decoration-color: {BORDER_2}; text-underline-offset: 3px; }}
a:hover {{ text-decoration-color: {INK_2}; }}
hr {{ border-color: {BORDER} !important; margin: 0.8rem 0 !important; }}
/* page title row */
.hk-title {{ display:flex; align-items:flex-end; justify-content:space-between; gap: 16px; padding: 0 0 12px 0; margin-bottom: 16px;
  border-bottom: 1px solid {BORDER}; }}
.hk-title h1 {{ margin: 0; padding: 0 !important; font-size: 1.5rem; font-weight: 600; color: {INK}; letter-spacing: -0.02em; line-height: 1.15; }}
.hk-title .sub {{ color: {MUTED}; font-size: 0.85rem; margin-top: 4px; }}
.hk-pill {{ display:inline-flex; align-items:center; gap: 8px; font-family: {MONO}; font-size: 0.74rem; color: {INK_2}; white-space: nowrap;
  background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 999px; padding: 5px 12px 5px 10px; }}
.hk-dot {{ width: 7px; height: 7px; border-radius: 50%; background: {GOOD}; box-shadow: 0 0 0 3px rgba(34,197,94,0.18); }}
.hk-dot.off {{ background: {CRITICAL}; box-shadow: 0 0 0 3px rgba(239,68,68,0.18); }}
/* metric tiles as uniform cards */
div[data-testid="stMetric"] {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: {RADIUS}px; padding: 14px 16px 12px 16px; }}
div[data-testid="stMetric"] label p {{ font-size: 0.7rem !important; font-weight: 600; color: {MUTED} !important; text-transform: uppercase;
  letter-spacing: 0.08em; }}
div[data-testid="stMetricValue"] {{ font-family: {MONO} !important; font-size: 1.6rem !important; font-weight: 500; color: {INK}; line-height: 1.2;
  letter-spacing: -0.02em; }}
div[data-testid="stMetricValue"] > div {{ font-family: {MONO} !important; }}
/* wraps rather than truncating: the delta carries the bootstrap interval, and a cut-off "95 % CI -0.0..." is worse than two lines */
div[data-testid="stMetricDelta"] {{ font-size: 0.78rem !important; color: {MUTED} !important; white-space: normal; line-height: 1.35;
  background: transparent !important; padding: 0 !important; margin-top: 2px; }}
div[data-testid="stMetricDelta"] > div {{ color: {MUTED} !important; background: transparent !important; padding: 0 !important;
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }}
div[data-testid="stMetricDelta"] p {{ color: {MUTED} !important; font-size: 0.78rem !important; white-space: normal !important;
  overflow: visible !important; text-overflow: clip !important; }}
div[data-testid="stMetricDelta"] svg {{ display: none; }}
/* strips / badges */
.hk-strip {{ font-family: {MONO}; font-size: 0.76rem; color: {INK_2}; background: {SURFACE_2}; border: 1px solid {BORDER};
  border-radius: 8px; padding: 8px 12px; margin: 4px 0 8px 0; overflow-x: auto; white-space: nowrap; }}
.hk-badges {{ display:flex; gap: 6px; flex-wrap: wrap; align-items:center; margin: 2px 0 8px 0; }}
.hk-badge {{ display:inline-flex; align-items:center; gap: 6px; font-size: 0.72rem; font-weight: 500; padding: 3px 9px; border-radius: 999px;
  border: 1px solid {BORDER}; color: {INK_2}; background: {SURFACE_2}; white-space: nowrap; }}
.hk-badge b {{ color: {INK}; font-weight: 600; font-family: {MONO}; }}
.hk-badge.warn {{ border-color: rgba(245,158,11,0.45); color: {WARNING}; }}
.hk-badge.crit {{ border-color: rgba(239,68,68,0.5); color: {CRITICAL}; }}
.hk-badge.ok {{ border-color: rgba(34,197,94,0.4); color: {GOOD}; }}
.hk-badge.accent {{ border-color: rgba(245,158,11,0.45); color: {ACCENT}; }}
/* legend strip */
.hk-legend {{ display:flex; gap: 20px; align-items:center; flex-wrap: wrap; font-size: 0.74rem; color: {INK_2}; margin: 8px 0 0 0; }}
.hk-legend .sw {{ display:inline-block; width: 56px; height: 6px; border-radius: 3px; vertical-align: middle; margin-right: 6px; }}
.hk-legend .dot {{ display:inline-block; width: 9px; height: 9px; border-radius: 50%; vertical-align: middle; margin-right: 6px; }}
.hk-legend .muted {{ color: {MUTED}; }}
/* sidebar */
section[data-testid="stSidebar"] {{ border-right: 1px solid {BORDER}; }}
section[data-testid="stSidebar"] .block-container {{ padding: 1.2rem 1rem; }}
.hk-brand {{ display:flex; align-items:center; gap: 10px; padding: 2px 0 14px 0; }}
.hk-brand .mark {{ width: 28px; height: 28px; border-radius: 8px; background: {SURFACE_3}; border: 1px solid {BORDER_2}; display:flex;
  align-items:center; justify-content:center; color: {ACCENT}; font-weight: 700; font-size: 0.8rem; font-family: {MONO}; }}
.hk-brand .name {{ font-weight: 600; font-size: 0.95rem; color: {INK}; letter-spacing: -0.01em; line-height: 1.1; }}
.hk-brand small {{ display:block; color: {MUTED}; font-weight: 500; font-size: 0.68rem; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 3px; }}
section[data-testid="stSidebar"] div[data-testid="stRadio"] > label {{ display: none; }}
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] {{ gap: 2px; }}
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label {{ padding: 6px 10px; border-radius: 8px; margin: 0; }}
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {{ background: {SURFACE_2}; }}
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label[data-selected="true"] {{ background: {SURFACE_2}; }}
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label > div > div > div:first-child {{ display: none; }}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label p {{ font-size: 0.9rem; font-weight: 500; color: {INK_2}; }}
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label[data-selected="true"] p {{ color: {INK}; }}
.hk-side-kv {{ font-size: 0.78rem; color: {INK_2}; line-height: 1.55; }}
.hk-side-kv .k {{ color: {MUTED}; font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; display:block; margin-top: 10px; }}
.hk-side-kv .v {{ color: {INK}; font-family: {MONO}; }}
/* widgets */
div[data-testid="stRadio"] div[role="radiogroup"] label p {{ font-size: 0.86rem; }}
div[data-testid="stCaptionContainer"] p, .stCaption p {{ color: {MUTED} !important; font-size: 0.8rem; line-height: 1.5; }}
div[data-testid="stExpander"] details {{ border: 1px solid {BORDER}; border-radius: {RADIUS}px; background: {SURFACE_2}; }}
div[data-testid="stExpander"] summary p {{ font-size: 0.86rem; font-weight: 500; color: {INK_2}; }}
div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: {RADIUS}px; overflow: hidden; }}
div[data-testid="stAlert"] {{ border-radius: {RADIUS}px; }}
div[data-testid="stPlotlyChart"] {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: {RADIUS}px; overflow: hidden; }}
div[data-testid="stDeckGlJsonChart"] {{ border: 1px solid {BORDER}; border-radius: {RADIUS}px; overflow: hidden; }}
div[data-testid="stDeckGlJsonChart"] canvas {{ border-radius: {RADIUS}px; }}
/* progress bars in tables pick up the accent */
div[data-testid="stDataFrame"] [role="progressbar"] {{ background: {ACCENT}; }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def title_row(title: str, subtitle: str = "", as_of: str = "", live: bool = True) -> None:
    """Clean page title row: title + one-line subtitle on the left, LIVE pill on the right."""
    dot = "hk-dot" if live else "hk-dot off"
    st.markdown(
        f'<div class="hk-title"><div><h1>{title}</h1><div class="sub">{subtitle}</div></div>'
        f'<div class="hk-pill"><span class="{dot}"></span>{"LIVE" if live else "STALE"} · {as_of}</div></div>',
        unsafe_allow_html=True)


def strip(text: str) -> None:
    st.markdown(f'<div class="hk-strip">{text}</div>', unsafe_allow_html=True)


def badge(text: str, kind: str = "") -> str:
    return f'<span class="hk-badge {kind}">{text}</span>'


def badges(*items: str) -> None:
    st.markdown('<div class="hk-badges">' + "".join(items) + "</div>", unsafe_allow_html=True)
