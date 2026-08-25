/** Shapes of web/public/data/*.json written by src/hkia/export_json.py */
export interface Meta {
  generated_at: string
  data_as_of: string | null
  flights_fetched_at: string | null
  last_score: string | null
  last_metar: string | null
  model_version: string | null
  dates: { yesterday: string; today: string; tomorrow: string }
  counts: {
    flights: number
    date_min: string
    date_max: string
    predictions: number
    yesterday_flights: number
    today_flights: number
    tomorrow_flights: number
  }
  airlines: Record<string, string>
  iata_to_icao: Record<string, string>
  airports: Record<string, { city: string; country: string }>
  hkia: { icao: string; iata: string; lat: number; lon: number }
  sources: Record<string, string>
}

export type FlightStatus = 'scheduled' | 'departed' | 'cancelled'

/** The inbound aircraft feeding this departure, written by src/hkia/export_json.py:inbound_by_flight. Only present
 *  for flights that have not left yet (same size discipline as `why`), and only when `aircraft_links` has a row.
 *  `flight_no`/`origin`/`sched_ts` describe the INBOUND arrival, not this departure. `used_by_model` is the exact
 *  predicate the model uses (a stand_gate link whose inbound was on blocks more than 2 h before this departure's
 *  scheduled time) — false for an adsb_hex link even when it looks just as informative, because the model never
 *  sees adsb_hex links at all. */
export interface Inbound {
  flight_no: string
  origin: string | null
  sched_ts: string | null
  actual_ts: string | null
  est_ts: string | null
  status: 'landed' | 'in_flight' | 'unknown'
  slack_min: number | null
  sched_slack_min: number | null
  confidence: number
  method: 'stand_gate' | 'adsb_hex'
  used_by_model: boolean
}

/** One attribution row of the "why this prediction" block, written by src/hkia/explain.py:
 *  `[direction, one-liner, probability points]` — direction +1 when the feature pushed P(delay > 15) up.
 *  The values are local SHAP contributions for that single prediction, converted from log-odds to probability
 *  points by linearising at the flight's own p (see the module docstring of hkia/explain.py). */
export type WhyItem = [dir: 1 | -1, text: string, pp: number]

export interface Flight {
  flight_no: string
  airline: string | null
  dest: string
  dest_all?: string
  sched_ts: string
  est_ts: string | null
  actual_ts: string | null
  status: FlightStatus
  terminal: string | null
  gate: string | null
  codeshares: string | null
  delay_min: number | null
  p: number | null
  pred_min: number | null
  scored_at: string | null
  /** top-3 drivers of the latest score; only written for flights that have not departed yet */
  why?: WhyItem[]
  /** [epoch_s, p, pred_min] */
  history?: [number, number | null, number | null][]
  /** the inbound aircraft; only written for flights that have not departed yet, and only with an aircraft_links row */
  inbound?: Inbound
}

export interface Departures {
  date: string
  n: number
  flights: Flight[]
}

export interface Patterns {
  summary: {
    n: number
    date_min: string
    date_max: string
    mean_delay: number
    median_delay: number
    pct15: number
    n_airlines: number
    n_dest: number
    window_days: number
  } | null
  heatmap?: {
    hours: number[]
    dow: string[]
    mean_delay: (number | null)[][]
    pct15: (number | null)[][]
    n: number[][]
  }
  airlines?: { code: string; name: string; n: number; mean_delay: number; pct15: number }[]
  destinations?: { code: string; city: string; country: string; n: number; mean_delay: number; pct15: number }[]
  daily?: { date: string; n: number; mean_delay: number; pct15: number; signal: number; tc_name: string | null }[]
  by_hour_top_airlines?: Record<string, { name: string; pct15: (number | null)[]; n: number[] }>
  typhoon?: {
    n_days: number
    n_other: number
    mean_delay: number
    pct15: number
    mean_delay_other: number
    pct15_other: number
    names: string[]
    days: { date: string; signal: number; tc_name: string | null; mean_delay: number; pct15: number }[]
    signal8_mean_delay: number | null
    signal8_days: string[]
  } | null
}

export interface MetricSet {
  auc?: number | null
  logloss?: number | null
  brier?: number | null
  mae?: number | null
}

/** AUC / Brier / MAE for one slice of the live window; auc is null when the slice holds a single class. */
export interface SliceMetrics {
  auc: number | null
  brier: number | null
  mae: number | null
}

export interface LiveDailyRow {
  date: string
  n: number
  delayed15_rate: number | null
  /** fewer than live_eval.min_slice_n flights — the AUC is noise, label it */
  thin: boolean
  /** first/last day of the rolling window: truncated, so not comparable with a full day */
  partial?: boolean
  model: SliceMetrics
  baseline?: SliceMetrics
}

/** Forecast horizon = scheduled_ts - scored_at (known when the score is written, independent of the outcome). */
export interface LeadBucket {
  label: string
  lo_min: number | null
  hi_min: number | null
  n: number
  thin: boolean
  delayed15_rate: number | null
  median_horizon_min?: number | null
  median_lead_min: number | null
  model: SliceMetrics
  baseline?: SliceMetrics
}

/** One matured prediction, for the notable-flights table. */
export interface NotableFlight {
  flight_no: string
  date: string
  sched_ts?: string
  airline: string | null
  dest: string | null
  p: number | null
  pred_min: number | null
  delay_min: number | null
  delayed15: 0 | 1
  lead_min: number | null
  horizon_min?: number | null
}

/** Every call published above `threshold`, hits and misses — the counterpart to the hand-picked notable table. */
export interface HighConfidenceRecord {
  threshold: number
  n: number
  n_late: number
  rate: number | null
}

export type DeltaKey = 'auc' | 'brier' | 'logloss' | 'mae'

/** Paired bootstrap over the matured flights: 95 % CI on (model - baseline), and whether it clears 0. */
export interface Bootstrap {
  n_boot: number
  ci: Partial<Record<DeltaKey, [number, number] | null>>
  beats_baseline: Partial<Record<DeltaKey, boolean | null>>
}

/** Everything the "model report card" needs; written by src/hkia/evaluate.compute into model.json. */
export interface LiveEval {
  window_days: number
  n_matured: number
  min_n: number
  min_slice_n?: number
  computed_at?: string
  status: string
  date_min?: string
  date_max?: string
  delayed15_rate?: number
  median_lead_min?: number
  model?: MetricSet
  baseline_airline_hour?: MetricSet & { error?: string }
  naive_rate?: MetricSet
  median_horizon_min?: number
  coverage?: { n_departed?: number; n_scored?: number; pct?: number | null; error?: string }
  deltas?: Partial<Record<DeltaKey, number | null>> | null
  bootstrap?: Bootstrap | null
  cal_min_n?: number
  daily?: LiveDailyRow[]
  lead_buckets?: LeadBucket[]
  calibration?: { bin: string; n: number; thin?: boolean; pred_mean: number; obs_rate: number }[]
  notable?: {
    confident_correct: NotableFlight[]
    worst_misses: NotableFlight[]
    high_confidence?: HighConfidenceRecord
  }
  by_model_version?: Record<string, number>
}

export interface ModelJson {
  manifest: {
    created_at: string
    git_sha: string
    xgboost: string
    n_features: number
    features: string[]
    categorical: string[]
    split: Record<
      'train' | 'val' | 'test',
      { date_min: string; date_max: string; n_rows: number; n_dates: number; delayed15_rate: number }
    >
    metrics: Record<string, MetricSet>
    ablation_test: Record<string, { n_features: number; auc: number; logloss: number; brier: number }>
    params: Record<string, unknown>
    clf_best_iteration: number
    reg_best_iteration: number
  } | null
  calibration: { bin: string; n: number; pred_mean: number; obs_rate: number }[]
  feature_importance: {
    importance_type: string
    top: number
    clf_delayed15: Record<string, number>
    reg_delay_min: Record<string, number>
  } | null
  live_eval: LiveEval
  interpretation_md: string
  limitations: string[]
}

export interface Weather {
  metar: {
    report_time: string
    raw_ob: string
    temp_c: number | null
    dewp_c: number | null
    wdir: number | null
    wspd_kt: number | null
    wgst_kt: number | null
    visib: string | null
    ceiling_ft: number | null
    flt_cat: string | null
    wx_string: string | null
    fetched_at: string
  } | null
  hko_warnings: { code: string; name: string; action: string; issue_time?: string; update_time?: string }[]
  hko_warnings_fetched_at: string | null
  tc_active: { signal: string; tc_name: string | null; direction: string | null; start_ts: string; end_ts: string }[]
  hko_current: {
    update_time: string
    humidity?: number | null
    temp_airport_c?: number | null
    temp_hko_c?: number | null
    rainfall_max_mm?: number | null
  } | null
}

/* ------------------------------------------------------------------ case_noul.json (src/hkia/case_study.py)
 * Static history: five fixed days of July 2026, generated once by `python -m hkia.case_study` and committed.
 * The ingest cron does NOT rewrite it, so unlike the other snapshots this one never changes between deploys. */

export interface CaseSignal {
  signal: number
  direction: string | null
  start: string
  end: string
  hours: number
}

/** One clock hour of the window; `mean_delay` is null when nothing departed that hour. */
export interface CaseHour {
  t: string
  signal: number
  n_sched: number
  n_departed: number
  n_cancelled: number
  n_labelled: number
  mean_delay: number | null
  p90_delay: number | null
  max_delay: number | null
  wspd_kt: number | null
  wgst_kt: number | null
  visib_sm: number | null
  flt_cat: string | null
  wx: string | null
}

export interface CaseTotals {
  n: number
  n_cancelled: number
  cancel_rate: number | null
  n_labelled: number
  n_over_clip: number
  mean_delay: number | null
  median_delay: number | null
  p90_delay: number | null
  pct15: number | null
}

export interface CaseWorstFlight {
  flight_no: string
  airline: string | null
  airline_name: string
  dest: string
  dest_city: string
  sched_ts: string
  actual_ts: string
  delay_min: number
  signal: number
  /** beyond the [-60, 600] min clip used for every average in the repo */
  over_clip: boolean
}

/** One slice of the retrospective. Read `mean_pred_delay` against `mean_obs_delay`: that gap is the story. */
export interface CaseRetroBlock {
  n: number
  obs_rate: number | null
  mean_p: number | null
  pct_flagged: number | null
  auc: number | null
  brier: number | null
  mae: number | null
  mean_pred_delay: number | null
  mean_obs_delay: number | null
}

export interface CaseStudy {
  generated_at: string
  regenerate: string
  static: boolean
  note: string
  episode: {
    tc_id: string
    name: string
    peak_signal: number
    first_signal: string | null
    all_clear: string | null
    sequence: string
    signals: CaseSignal[]
  }
  window: { start: string; end: string; tz: string; days: string[] }
  other_episodes: {
    tc_id: string
    name: string | null
    peak_signal: number
    start: string
    end: string
    kind: string
  }[]
  /** strong-monsoon rows share one tc_id, so they are counted rather than listed as a single bogus span */
  other_monsoon: { n: number; date_min: string; date_max: string } | null
  headline: {
    peak_signal: number
    n_flights_window: number
    n_flights_episode: number
    n_cancelled_episode: number
    cancel_rate_episode: number | null
    peak_hour: string | null
    peak_hour_mean_delay: number | null
    peak_hour_n: number | null
    peak_gust_kt: number | null
    min_visib_sm: number | null
    hours_to_recover: number | null
    n_hours_no_departures: number
  }
  hourly: CaseHour[]
  by_signal: ({ signal: number } & CaseTotals)[]
  baseline: { label: string; date_min: string; date_max: string; n_days: number } & CaseTotals
  worst_flights: CaseWorstFlight[]
  cancellations: {
    total: number
    by_airline: { airline: string; name: string; n_cancelled: number; n_sched: number; rate: number | null }[]
    by_dest: { dest: string; city: string; n_cancelled: number }[]
    by_day: { date: string; n_sched: number; n_cancelled: number; rate: number | null }[]
  }
  recovery: {
    all_clear_ts: string | null
    recovered_at: string | null
    hours_to_recover: number | null
    baseline_mean_delay: number | null
    min_n: number
    rule?: string
  }
  /** null when the artefact was built without the model. ALWAYS in-sample — show the flag on the page, not only in prose. */
  retrospective: {
    in_sample: boolean
    split_containing_episode: string
    val_dates: [string, string]
    model_version: string
    live_scoring_began: string
    flag_threshold: number
    note: string
    overall: CaseRetroBlock
    by_signal: ({ signal: number } & CaseRetroBlock)[]
    hourly: {
      t: string
      n: number
      mean_p: number | null
      mean_pred_delay: number | null
      mean_obs_delay: number | null
    }[]
  } | null
  clip: { min: number; max: number; note: string }
  sources: Record<string, string>
}
