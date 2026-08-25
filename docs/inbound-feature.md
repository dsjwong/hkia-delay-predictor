# Inbound-aircraft turnaround signal

*Phase 1 built 2026-08-20. Phase 2 built 2026-08-24 — and it does **not** ship the feature phase 1 advertised. The
in-sample signal below (r = 0.387) was leaky; what survives the leak fix is a **long-turnaround indicator**, mostly
carried by a single binary. Read "Phase 2 — what was actually built" before quoting any number from phase 1.*

**The idea.** A departure cannot leave until its aircraft has arrived, been cleaned, refuelled and reloaded. If the
aircraft that is meant to operate your 18:40 to Bangkok is still 40 minutes out, your 18:40 is not leaving at 18:40. This
is the single strongest non-weather predictor of departure delay in the literature, and the model does not have it: the
current features are schedule, airline, destination, congestion and weather — all of which describe the *slot*, none of
which describe the *aircraft*.

**Why it is not a five-minute job.** The AAHK departures feed carries no tail number and no inbound flight number. There
is nothing in the departures data that says which aircraft is coming. The link has to be inferred from other sources,
which is what phase 1 builds.

---

## What phase 1 built

Four new tables, all filled by the existing 30-minute cron (`.github/workflows/ingest.yml`) and the nightly
`backfill.yml`. Nothing scores anything yet — the point is to **start the clock** so the data exists when phase 2 wants it.

| table | module | what it holds |
|---|---|---|
| `arrivals` | `hkia.ingest_arrivals` | the arrivals side of the same AAHK endpoint, ~450 rows/day |
| `adsb_snapshots` | `hkia.ingest_adsb` | one ADS-B frame per cron run, ~55 aircraft, 30-day retention |
| `aircraft_links` | `hkia.rotations` | inferred arrival → departure aircraft rotations, tagged by method |
| — | `hkia.adsb` | the provider chain, extracted out of `app/live_map.py` so app and cron share one feed |

### 1. Arrivals (`arrivals`)

Verified on 2026-08-20:

```
https://www.hongkongairport.com/flightinfo-rest/rest/flights/past?date=YYYY-MM-DD&lang=en&cargo=false&arrival=true
```

200 OK, the same day-object shape as departures, the same rolling ~91-day window, ~440–455 passenger arrivals/day.
Row fields differ: `origin` (list of IATA) instead of `destination`, `stand` instead of `gate`, plus `hall` and `baggage`.

Status vocabulary, and why three timestamp columns rather than one:

| status | column | meaning |
|---|---|---|
| `At gate HH:MM [(DD/MM/YYYY)]` | `actual_ts` | **on blocks** — the moment the turnaround clock starts |
| `Landed HH:MM` | `landed_ts` | touchdown; still taxiing, not yet available for the turnaround |
| `Est at HH:MM [(DD/MM/YYYY)]` | `estimated_ts` | the airport's live estimate — **the only inbound time known before it lands** |
| `Cancelled`, `""` | — | nothing parsed |

That last row is the one that matters for phase 2: `estimated_ts` is the leakage-free version of "how late is the inbound".

Backfilled locally over the full window: **40,226 arrivals across 93 days, 39,090 with an on-blocks time, 39,122 with a
stand.** The backfill was *not* committed (`data/hkia.db` is the CI bot's file); `backfill.yml` now runs
`ingest_arrivals --fill-gaps` nightly, which re-fetches only window days that are missing or under 300 rows, so the
shared database fills itself in and self-heals afterwards at near-zero request cost.

### 2. ADS-B snapshots (`adsb_snapshots`)

Every cron run appends one frame from `hkia.adsb.fetch_adsb()` — the same provider chain the live map uses
(adsb.lol → OpenSky → adsb.fi → airplanes.live). ~55 rows/run × 48 runs/day ≈ 2,600 rows/day, pruned to 30 days
(~80 k rows, a few MB). Stored per aircraft: `fetched_at`, `hex`, `callsign`, `registration`, `ac_type`, position,
altitude, ground speed, track, `dst_nm`, `provider`.

- **`hex`** (the ICAO 24-bit address) is the stable airframe identity. It is all the linkage needs.
- **`registration`** is a bonus: the readsb-family feeds carry `r`, OpenSky's `/states/all` does not. On an OpenSky run
  the column is NULL. Turning a hex into a registration offline would mean shipping the OpenSky aircraft database
  (~500 k rows) — **noted, deliberately not built.** Registration is nicer to *display*; it is not needed to *link*.
- **Coverage caveat, and it is a real one:** the feed is a 100 nm ring, so an inbound is only visible for the last
  ~15–20 minutes of its flight, and a 30-minute poll can miss it entirely. ADS-B tells us *which* aircraft turned
  around; it does not tell us how late that aircraft was an hour out. That number comes from `arrivals.estimated_ts`.

### 3. The linkage (`aircraft_links`)

Two independent methods write into one table, each row tagged with its `method`, so they can be compared head-to-head
on the same departures later.

#### `adsb_hex` — ground truth, no history

A hex seen transmitting an arrival callsign and later the same day a departure callsign is one aircraft turning around.
Callsign ↔ flight matching reuses the live map's rule (ICAO airline code + flight number; `CPA261` ↔ `CX 261`, with an
IATA→ICAO map built from our own rows so a feed that sends `UO755` still matches `HKE`).

Exact when it fires. It just cannot fire retrospectively — snapshots start 2026-08-20 — and the 100 nm ring plus the
30-minute poll mean it will only ever catch a fraction of rotations. **Expected coverage: low, and it accrues slowly.**

#### `stand_gate` — a proxy that works over the whole backfill

Arrivals publish `stand` (`N36`, `D214`, `W65`); departures publish `gate` (`36`, `214`, `65`). These are the *same*
numbering with an apron-area letter on the arrivals side. Evidence, from 2026-08-19:

- 373 of 438 departures sat at a position that also took an arrival that day.
- Per-position counts line up almost exactly — position 10: 9 arrivals / 9 departures, 68: 8/8, 209: 7/7, 214: 7/7.
- Positions with arrivals but no departures are all remote stands (`S102`, `W121L`, `D3xx`), whose passengers leave from
  bus gates (`227–230`, `511–524`) — exactly the asymmetry you would expect if the mapping is real.

So: **pair each arrival at a position with the first departure from that position after it and before the next arrival
there.** Guards — minimum 25 min (below that it is two aircraft sharing a stand, not a turnaround), maximum 12 h
(beyond that it has been towed away and back), cancelled departures excluded, and if two departures fall inside one
arrival's window only the first is linked (`confidence` 0.6) because the second could be an aircraft towed in.

The failure mode is towing: an aircraft moved off-stand and replaced between the two events produces a wrong pair.

### Measured coverage and accuracy (backfilled window, 2026-05-16 → 2026-08-20)

```
stand_gate:  32,312 links over 92 days, mean turnaround 155 min, airline agreement 99.3% (32,085/32,312)
  adsb_hex:  no links yet (snapshots began 2026-08-20)
   overall:  32,312/41,765 departures have an inbound link (77.4%)
```

**Airline agreement is the honest accuracy check.** An aircraft normally arrives and departs for the same carrier, so a
wrong pairing usually shows up as a carrier mismatch. Against two null models on exactly the same linked arrivals:

| pairing | airline agreement |
|---|---|
| **`stand_gate` as built** | **99.3 %** |
| a *random* departure from the same position that day | 49.2 % |
| a *random* departure that day, any gate | 19.6 % |

The position alone buys 49 %; the time ordering on top of it buys the remaining 50 points. That is the proxy earning its
keep, not the stand allocation flattering it. It is still a proxy — the plan is to re-run this comparison against
`adsb_hex` links once ~2 weeks of ADS-B history exists, which measures the proxy against ground truth on the same flights.

Per-day coverage splits as expected: **~85 % on a completed day**, ~65 % on the day in progress, **0 % on future days** —
because `gate` and `stand` are only published ~2–3 h ahead (measured 2026-08-20: 25/25 departures within 1 h had a gate,
2/20 at 4 h out, 0/2 at 7 h out). This is the central constraint on phase 2 and is discussed below.

### Does the signal exist at all?

On the 32,212 linked pairs where both actuals are known — in-sample exploration, not a model:

| inbound lateness (actual − scheduled) | n | mean departure delay | P(delay > 15) |
|---|---|---|---|
| early / on time | 16,459 | 10.0 min | 21.1 % |
| 0–15 min late | 7,376 | 14.4 min | 29.2 % |
| 15–30 | 3,593 | 21.0 min | 43.8 % |
| 30–60 | 2,867 | 29.5 min | 57.6 % |
| > 60 | 1,917 | 55.4 min | 62.2 % |

Pearson *r* (inbound lateness, departure delay) = **0.387**. Expressed as slack instead — scheduled departure minus
actual on-blocks — a turnaround under 60 minutes carries P(delay > 15) of **65.9 %** against ~20 % for everything
longer. Monotone, large, and on the right side of plausible. The feature is worth building.

> **This table is leaky and its headline number does not survive phase 2.** It uses the inbound's *final* on-blocks
> time for every pair — including inbounds that landed *after* the departure's decision point, and (worse) after the
> departure itself. A model cannot know that. Under the leak-free rule below the same relationship shrinks to
> *r* ≈ 0.04 and a gradient of 0.19 → 0.29 in P(delay > 15). Keep the table for the intuition, not for the magnitude.

---

## Phase 2 — what was actually built

### The leak, and what is left after fixing it

Three separate leaks had to come out of the phase-1 construction. Two are about *values*, one is about the *link*:

1. **Post-cutoff on-blocks times.** The signal table above uses `arr_actual_ts` unconditionally. The feature may only
   use the inbound if it was on blocks **strictly before `scheduled_ts − 2 h`** (`hkia.features.PIT_LAG`, the same
   cutoff the rolling delay block already used). Anything later is the future.
2. **Not-yet-reached cutoffs at serving time.** A flight scored five hours out has not reached its own cutoff, so it
   must score as if it had no link. `hkia.predict` passes the scoring timestamp into `build_features`, which gates the
   block on it — train and serve then agree by construction (`tests/test_features.py` asserts the two paths produce
   identical rows).
3. **Label-dependent pairing.** The stored `stand_gate` links pair each arrival with the first departure from that
   stand *after it, by actual departure time*. Actual departure time **is** the label. Links for training are therefore
   rebuilt from **scheduled** departure times (`hkia.rotations --events sched`); `data/features.meta.json` records which
   event source built the parquet, and `scripts/inbound_gate.py` refuses to ship a model built on `actual`.

What is left after all three:

| | leaky (phase 1) | leak-free (phase 2) |
|---|---|---|
| P(delay > 15) gradient across inbound lateness | 0.21 → 0.62 | ~0.19 → ~0.29 |
| Pearson *r* (inbound lateness, departure delay) | 0.387 | ≈ 0.04 |

**The value features are nearly flat. The carrier of the signal is the binary `inbound_known`** — was the aircraft on
stand at all, two hours out: **P(delay > 15) = 0.213** when it was, **0.356** when it was not. That is the feature this
phase ships, and it should be described as what it is: an aircraft that is already on stand two hours before departure
is having a long, calm turnaround. It says nothing about an inbound that is still in the air — the case the phase-1
write-up was actually excited about.

### `adsb_hex` links are validation-only — and the timestamp trap

`adsb_hex` links are ground truth for *which* aircraft turned around, so they are kept for validating the proxy, and
they are **excluded from the feature build** (`load_links` filters `method='stand_gate'`; 465 departures carry both,
which would otherwise duplicate feature rows).

They are also not usable as features for a second reason. Checking when the links were built against when the
departures left: **about 22 of 501 `adsb_hex` links were built before their departure actually departed** — a lower
bound, because `built_at` records the *last* change to the row, not the first. The rest were built after the fact and
could not have been used at scoring time.

> **The trap, written down because it cost real time:** `built_at` is UTC (`...+00:00`) and `actual_ts` is HKT
> (`...+08:00`). Comparing them as **strings** — which is tempting, since both are ISO-8601 in the same table — makes
> almost every link look "built before departure" and gives ≈ 499 of 501. The 8-hour offset is the entire result.
> Normalise to a single offset (parse, then compare) before drawing any conclusion from these two columns.

### Coverage: train ≈ 0.32, serve ≈ 0.23

The parquet knows the inbound of ~**32 %** of departures at the cutoff. Deployment knows ~**23 %** — the stand is
published only ~2–3 h ahead, and every day-ahead row is knowably empty. Training on the richer distribution ships a
model that leans on a feature it usually will not have, so `hkia.train --inbound-dropout` masks a random share of the
linked rows back to the exact serve-time encoding (`inbound_known = 0`, the four value features NaN) — in **all three
splits**, validation included, so early stopping also sees the deployment distribution. The parquet is never modified.
`hkia.predict` logs the realised serve-time coverage per horizon bucket to `ingest_log` every run, so the assumed rate
can be re-checked (and the dropout re-tuned) instead of being believed.

### The ship gate

`scripts/inbound_gate.py` — GATE-A..D, exits non-zero on the first failure: a bootstrap CI on ΔAUC entirely above zero,
mean ΔMAE over five test-mask seeds no worse, no day-ahead probability inflation against the deployed models on the
same scratch db, and a MANIFEST that proves the leak-free build (`links_event_source == "sched"`, the expected dropout,
per-split coverage, the `no_inbound` ablation row, the sensitivity row). If it fails, the block does not ship.

### Phase 3 — the feature phase 1 actually wanted

A true inbound-ETA feature — "your aircraft is 40 minutes out" — needs the inbound's *estimated* arrival as it was
known at scoring time. That is now being recorded (`arrivals_state_hist`), which unblocks it; it was not buildable when
phase 1 was written, and it is not what phase 2 ships.

---

## Phase 2 — the original plan (superseded by the section above)

**The feature, stated so that it cannot leak.** At scoring time *t* for a departure scheduled at *s*, the model may use
only what was knowable at *t*:

- `inbound_linked` — is there a link for this departure at all (0/1)? Missingness is itself informative and must be a
  category, not an imputed zero.
- `inbound_eta_slack_min` = *s* − (inbound's **estimated or actual** arrival **as known at t**). Never the arrival time
  that was eventually recorded.
- `inbound_not_yet_landed` — at *t*, had the inbound gone on blocks? This is the "your aircraft is still 40 minutes out"
  flag in its rawest form.
- `inbound_lateness_min` = estimated/actual arrival known at *t* − inbound's scheduled arrival.
- `link_confidence` and `link_method`, so the model can discount proxy links.

**The rule, written down once so it is not lost:** `arrivals.actual_ts` for an inbound that had not landed at *t* is the
future. It may be used to build labels and to evaluate, never as a feature. The safe construction is to score from the
`predictions`-table timeline the project already keeps — every prediction row carries its `scored_at`, so the inbound
state must be reconstructed as of that timestamp, not as of "now". The existing time-based split protects against
train/test leakage; this is a different failure, *within-row* leakage, and the split will not catch it.

**Horizon reality.** Because gates and stands appear only ~2–3 h before departure, phase 2's feature is a **short-horizon
feature**: rich inside ~3 h, absent day-ahead. Two mitigations, in order of preference:

1. Accept it. The dashboard already re-scores every 30 minutes; a feature that sharpens the last three hours sharpens
   exactly the window a passenger actually looks at. Report metrics split by lead-time bucket (`evaluate.py` already
   buckets by horizon) rather than as one blended number that hides where the gain is.
2. A learned rotation prior for day-ahead scoring: the historical link table gives, per departure flight number, which
   arrival flight number usually feeds it. Measured on the backfill — for the 522 departure numbers with ≥ 5 links, the
   modal inbound is the right one **54.4 %** of the time, and 157 of them always have the same inbound. So this is a
   *weak prior*, not a link: usable as "the flight that usually feeds this one is running 40 late", with the confidence
   it deserves, and not worth building before route 1 has proven the feature works at all.

**Also deliberately deferred:** the live-map "aircraft inbound" indicator, and an `explain.py` template for the new
feature. Both are downstream of the model actually using it.

**When to retrain.** ~~Two things have to be true … two to three weeks of scoring-time history.~~ *Superseded.* That note
assumed the whole plan above had to wait for `arrivals.estimated_ts` history. It does not: the *existence* half of the
feature (`inbound_known` plus the turnaround values, gated at scheduled − 2 h) needs only the backfilled `stand_gate`
links, which already exist — so phase 2 was built on 2026-08-24 rather than waiting. What genuinely still needs
scoring-time history is the **inbound-ETA** feature, i.e. phase 3, and the recorder for it (`arrivals_state_hist`) is
now running.

---

## Backlog

- **Phase 3 — inbound ETA as known at scoring time.** Unblocked by the `arrivals_state_hist` recorder; needs a few
  weeks of it before there is anything to fit. This is the "your aircraft is still 40 minutes out" feature that phase 1
  described and phase 2 does **not** ship.
- **Re-check the serve-time coverage assumption.** `hkia.predict` logs inbound coverage per horizon bucket to
  `ingest_log` every run; if the realised rate drifts away from the ~0.23 the dropout was set from, retune
  `--inbound-dropout` and re-run the gate.
- **`stand_gate` vs `adsb_hex` agreement on the same flights**, to put a real error bar on the proxy — now that ADS-B
  links are accruing. Mind the timestamp trap above when touching `built_at`.
