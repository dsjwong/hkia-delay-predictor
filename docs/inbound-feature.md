# Inbound-aircraft turnaround signal

*Phase 1 built 2026-08-20. Phase 2 (retraining) deliberately not built — see the backlog note at the end.*

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

---

## Phase 2 — the plan (not built)

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

**When to retrain.** Two things have to be true. The `stand_gate` proxy already has 92 days of history, so the training
set is not the blocker — the blocker is *scoring-time* history: `arrivals.estimated_ts` snapshots and `adsb_hex` links
only start accruing 2026-08-20, and reconstructing "what did we know at *t*" needs a few weeks of them. Two to three
weeks gives ~1,000 ADS-B-linked rotations to validate the proxy against, and enough estimated-arrival history to build
the leakage-free feature honestly.

---

## Backlog

- **Retrain with inbound features ~2026-09-10**, when the accumulated data suffices. Before then: (a) re-run the
  `stand_gate` vs `adsb_hex` agreement check to put a real error bar on the proxy, (b) confirm `arrivals.estimated_ts`
  is being captured densely enough by the 30-minute cron to reconstruct scoring-time state.
