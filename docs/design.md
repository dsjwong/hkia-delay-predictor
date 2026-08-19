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
