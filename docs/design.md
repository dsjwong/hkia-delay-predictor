# Dashboard design notes

Neutral dark-grey system (shadcn/ui "zinc" dark; the Linear / Vercel-dashboard look). Tokens live in `app/theme.py` and are
mirrored in `.streamlit/config.toml` — change both together. The React app in `web/` uses the same tokens.

- **Tokens.** Page `#09090b` (zinc-950) · cards / sidebar `#18181b` (zinc-900) · elevated (code, tooltips, hover) `#1f1f23` ·
  hairline border `#27272a` (zinc-800), hover border `#3f3f46` · text `#fafafa` / `#a1a1aa` / `#71717a` (zinc-50 / 400 / 500).
  One accent, amber `#f59e0b`; status colours (`#22c55e` good, `#f59e0b` warning, `#ef4444` critical) are reserved for badges, never series. No blue in chrome.
- **What each colour means.** Amber = P(delay > 15) and anything the model predicts (tracked departures on the map via the ramp
  `#6b4608 → #ffbf3d`, prediction series in charts as `#c9820c`, progress bars, selected nav / widgets). Zinc = observed, neutral or
  other (other traffic on the map `#a1a1aa → #f4f4f5` by altitude, single-series magnitude bars `#a1a1aa`, the heatmap ramp
  `#45454c → #ececef`). Green dot = live feed. Blue `#3d87e0` appears only as the neutral categorical for "tracked, not scored".
  Every palette is validated with the dataviz skill's `validate_palette.js` on `#09090b`: categorical `#c9820c #3d87e0 #14a88d #9b6fe0`
  adjacent ALL PASS (worst CVD dE 14.0, normal 17.4), first three all-pairs PASS; amber ramp PASS (light end 2.37:1, hue spread 8 deg); zinc ramp PASS.
- **Type.** Inter (system-ui fallback) at tight tracking (-0.006 em body, -0.02 em titles); scale 24 / 17 / 15 / 13 / 11 px —
  page title 600, section labels 11 px small-caps zinc-500 with 0.08 em tracking, captions 13 px zinc-500 and never more than one line.
  Numbers (metric tiles, METAR, badges, "data as of") in the system mono stack.
- **Spacing and surfaces.** 8-px grid (8 / 16 / 24 / 32); cards and charts 12-px radius with a 1-px `#27272a` border, no shadow, no glow;
  metric tiles are uniform cards (label / big mono number / muted caption); tables have subtle row lines, no zebra; Streamlit's coloured
  header strip, toolbar and footer are hidden; the sidebar is wordmark + nav + "data as of" block.
- **Charts.** One plotly template (`hkia_zinc`): card-coloured paper, transparent plot, hairline `#27272a` y-grid only, zinc-400 ticks,
  1.5-px lines, 2-px gaps between bars and cells, legend for every chart with >= 2 series, text never in the series colour, no dual axes.
  Live map: CARTO dark-matter basemap (grey), map >= 70 % of the row, compact legend strip under the map, tiles / METAR / tracked table on the right.
