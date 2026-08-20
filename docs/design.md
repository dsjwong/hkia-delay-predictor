# Web app design system (`web/`)

Neutral dark-grey, one warm accent. The goal is a product look (Linear / Vercel dashboard / shadcn "zinc"), not a themed radar
screen: quiet surfaces, hairline borders, Inter, tight headings, tabular figures, and colour that always *means* something.

## Library choice
- **shadcn/ui-style primitives written in-repo** (`web/src/components/ui/`: button, badge, card, tile, tooltip, sheet, segmented,
  skeleton, empty) on top of Tailwind 4 + `class-variance-authority` + `tailwind-merge`, and **Recharts** for every chart, with one shared
  theme (`web/src/charts/theme.tsx`, `tokens.ts`). The zinc token values are shadcn's own.
- **Tremor was evaluated and rejected** (decided at the start of the overhaul): `@tremor/react` 3.18 peer-depends on React 18 and needs
  the Tailwind 3 preset/config; the app is React 19 + Tailwind 4 (CSS-first `@theme`), so it would have meant a second Tailwind pipeline
  for ~6 components we already have. Tremor "Raw" is copy-paste code that also relies on Radix + Recharts — the in-repo primitives are
  the same idea with fewer bytes. `npx shadcn add` was not needed: no Radix dependency, the seven primitives are ~250 lines total and
  keyboard/ARIA behaviour is hand-checked (Esc closes the sheet, arrow keys move the segmented control, every icon button has an
  `aria-label`).
- **Inter** is bundled via `@fontsource-variable/inter` (latin subset ~48 KB woff2, loaded by `unicode-range`; no external font CDN;
  `system-ui` fallback in the stack).

## Tokens (`web/src/index.css` `@theme`, mirrored in `web/src/lib/theme.ts`)
| token | value | use |
|---|---|---|
| `bg` | `#09090b` zinc-950 | page |
| `card` | `#18181b` zinc-900 | cards, panels, sticky table header |
| `elev` | `#1f1f23` | inputs, hover rows, tooltips, skeletons |
| `elev-2` | `#27272a` zinc-800 | pressed / selected |
| `border` | `#27272a` zinc-800 | hairlines (1 px everywhere) |
| `border-2` | `#3f3f46` zinc-700 | focused input, stronger separators |
| `ink` / `ink-2` / `muted` | `#fafafa` zinc-50 / `#a1a1aa` zinc-400 / `#71717a` zinc-500 | primary / secondary / tertiary text, axis ticks |
| `accent` | `#f59e0b` amber-500 | **P(delay > 15) only** (bars, tile tone, selected-plane ring, KPI that *is* a delay figure) |
| `good` | `#22c55e` | LIVE dot, "departed", hit |
| `warning` | `#f59e0b` | HKO warnings / typhoon callout (same amber family — weather is a delay driver) |
| `critical` | `#ef4444` | cancelled, STALE, feed down |

No blue chrome anywhere; links are `ink` with a `border-2` underline.

### Colour meaning in charts (`web/src/charts/tokens.ts`)
- Categorical slots, fixed order, **validated** with the dataviz skill's `validate_palette.js` on `#18181b` (dark): `SERIES_1 #d97706`
  amber-600 (model / predicted / single-series bars), `SERIES_2 #0d9488` teal-600 (observed / actual / TC-signal days), `SERIES_3 #8b5cf6`,
  `SERIES_4 #db2777` — all five checks PASS (worst adjacent CVD ΔE 10.4, normal-vision 24.3, ≥ 3:1 contrast).
- `AMBER_RAMP` `#78350f → #b45309 → #d97706 → #f59e0b → #fcd34d`: P(delay > 15) 0 → 1 — plane icons, PBar, flight-card hero figure.
- `HEAT_RAMP` `#2a1a08 → #f7c55a`: heatmap magnitude (mean delay / late share) — same hue so "more amber = more delay" holds app-wide.
- Live **model report card** (Model route, `web/src/charts/ReportCharts.tsx` + `web/src/components/ReportCard.tsx`): two series only —
  `SERIES_1` = the model, `SERIES_2` = the airline × hour baseline — with a legend on every chart and a `NEUTRAL` 0.5 coin-flip reference
  line on every AUC chart, because an AUC axis without that anchor flatters the model. Daily AUC uses a round-tenth y range that always
  keeps 0.5 in view; horizon bars start at 0. Outcome badges in the notable-flights table pair the colour with a ✓/✗ icon and the words.
  The Streamlit twin (`app/charts.py: live_daily_auc, lead_bucket_bars`) uses the same meaning in the Streamlit slots (amber `#c9820c`
  model, teal `#14a88d` baseline — re-validated on `#18181b`, all checks PASS).
  **Uncertainty is part of the design, not a footnote.** A delta pill is only `good`-green when its 95 % bootstrap interval excludes 0;
  otherwise it is the neutral `default` variant and carries the words "within noise" next to the interval — green is reserved for a claim
  the data supports. Calibration bins under `cal_min_n` flights are drawn **hollow** (card fill, `SERIES_1` stroke) and the connecting
  line skips them, so three coin flips cannot read as a trend; thin AUC slices keep their bar but are labelled `thin` with their `n`.
  Every report-card chart carries `role="img"` + an `aria-label` that reads out its numbers, because the values otherwise exist only in
  a mouse-only tooltip.
- **"Why this prediction"** (flight card, `web/src/components/FlightCard.tsx: WhyBlock`; Streamlit twin `app/theme.py: why_lines`): three rows,
  each an arrow + one plain-English line + the push in probability points. `SERIES_1` amber = pushed P(delay > 15) **up**, `SERIES_2` teal =
  pushed it **down** — the same two-series meaning as the report card, and the direction is carried by the arrow glyph, the signed number and a
  visually-hidden "raises/lowers the probability", never by the colour alone. No bar chart: three signed numbers do not need axes, and a
  SHAP bar chart invites reading the three as if they summed to the probability, which they do not.
- `NEUTRAL #52525b` for reference lines (perfect-calibration diagonal, P = 0.5 line). Grid `#27272a` solid hairline, no dashes. One axis
  per chart; legends for ≥ 2 series; `TipBox` tooltip on every mark; text always in text tokens.
- Map: other traffic zinc-500 → zinc-100 by altitude, tracked-not-scored zinc-50, tracked-scored amber ramp, hover ring zinc-50, selected
  ring amber, rings zinc-400 @ 22 %, HKIA marker amber.

## Type scale
Inter Variable, `cv11`+`ss01` features. Page title `text-xl font-semibold tracking-tight`; card title `text-sm font-semibold`; body
`text-sm`; meta `text-xs text-muted`; kicker `.hk-kicker` = 0.7 rem uppercase 0.06 em zinc-500; KPI value 1.6 rem semibold
`tracking -0.02em` (proportional figures); tables / axis ticks / times `tabular-nums` (`.hk-num`); METAR and feed chips `font-mono`.

## Spacing & shape
8-px grid (`gap-3` tiles, `gap-4` chart grid, `space-y-5` page sections, `p-4` card padding); card radius 12 px (`--radius-card`), inputs
and buttons 6–8 px, pills full; hairline borders only — no shadows on cards, no gradients, no glows (the only shadow is under popovers /
the sheet).

## Layout
- App shell: 48-px sticky top bar (wordmark · quiet tabs with a 1-px underline · LIVE pill with data-as-of HKT · GitHub icon); no sidebar;
  on `< md` the nav becomes a fixed bottom tab bar with lucide icons.
- **Live map**: map fills `100dvh − header`; floating translucent panels (`.hk-glass` = card @ 80 % + `backdrop-blur`): top-left stat chips
  (aircraft in range, tracked departures, feed provider + age in seconds), right 372-px panel (METAR strip → tracked departures → recent
  departures; selecting a plane or a row slides the flight card into the same panel), legend bottom-left above the attribution, zoom
  control bottom-right (offset clear of the panel). On `< lg` the map is 58 dvh and the panel stacks beneath it.
- Other routes: `max-w-[1400px]` container, title row, KPI tile row, 2-column card grid of charts, tables in cards with a sticky header and
  their own scroll region. Every async block has a skeleton (`Skeleton*`) and an `Empty` / error state.

## Accessibility
`:focus-visible` 2-px zinc-50 ring; segmented controls are `role=group` with arrow-key movement; list rows are real `<button>`s or
`role=button` rows with Enter/Space; all icon buttons carry `aria-label`; `prefers-reduced-motion` disables the LIVE pulse, skeleton
shimmer, sheet slide and the plane dead-reckoning glide (positions then jump per poll).

---

# Streamlit dashboard (`app/`) — design notes

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
