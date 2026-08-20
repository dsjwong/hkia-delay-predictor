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
  /** [epoch_s, p, pred_min] */
  history?: [number, number | null, number | null][]
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
