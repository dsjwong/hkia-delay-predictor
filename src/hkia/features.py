"""Feature/label builder: one row per HKIA passenger departure -> data/features.parquet.

Usage: python -m hkia.features [--out data/features.parquet]

Rules (see docs/features.md for the full dictionary):
- label delay_min = actual_ts - scheduled_ts in minutes; rows with delay < -60 or > 600 are dropped (counted in log)
- cancelled flights are kept with cancelled=1 and NaN label; unlabelled (in-progress/blank status) rows are dropped
- weather = latest METAR observation strictly before scheduled time (asof join, 3 h tolerance)
- rolling delay features are point-in-time: only flights whose actual_ts < scheduled_ts - 2 h contribute
- inbound (turnaround) features use the linked inbound aircraft only if it was on blocks before scheduled_ts - 2 h
"""
import argparse
import datetime as dt
import json
import logging
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .db import connect, ROOT
from .holidays import holiday_dates
from .regions import region_of

log = logging.getLogger("hkia.features")
HKT = "Asia/Hong_Kong"
DELAY_MIN, DELAY_MAX = -60, 600
TOP_DEST_N = 30
PIT_LAG = pd.Timedelta(hours=2)   # rolling features may only use flights that departed >= 2 h before scheduled

CATEGORICAL = ["airline", "dest", "dest_region", "terminal", "flt_cat"]
NUMERIC = ["sched_hour", "sched_dow", "sched_minute_of_day", "is_holiday", "is_weekend",
           "cong_pm60", "cong_same_hour", "cong_pm30", "n_dest_legs",
           "temp_c", "dewp_c", "wdir", "wspd_kt", "wgst_kt", "visib_sm", "ceiling_ft",
           "wx_rain", "wx_ts", "wx_fog", "metar_age_min",
           "tc_signal", "msn_signal",
           "airline_prevday_mean_delay", "airline_prevday_n", "airline_sameday_mean_delay", "airline_sameday_n",
           "airport_sameday_mean_delay", "airport_sameday_n",
           "inbound_known", "inbound_actual_slack_min", "inbound_lateness_min", "inbound_sched_slack_min",
           "inbound_confidence"]
FEATURES = CATEGORICAL + NUMERIC
INBOUND = [f for f in NUMERIC if f.startswith("inbound_")]


# ---------- loading ----------

def load_flights(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT date, flight_no, airline, destination, scheduled_ts, actual_ts, status_raw, terminal FROM flights", conn)
    df["scheduled_ts"] = pd.to_datetime(df["scheduled_ts"], utc=True)
    df["actual_ts"] = pd.to_datetime(df["actual_ts"], utc=True)
    df["cancelled"] = (df["status_raw"].fillna("").str.strip().str.lower() == "cancelled").astype(int)
    return df.sort_values("scheduled_ts").reset_index(drop=True)


def _parse_visib(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    s = str(v).strip()
    if s.endswith("+"):
        return 6.21  # aviationweather "6+" == IEM 9999 m
    try:
        return float(s)
    except ValueError:
        return np.nan


def load_metar(conn) -> pd.DataFrame:
    """Union of the IEM backfill (metar_hist) and the live aviationweather table (metar), UTC, deduped by minute."""
    hist = pd.read_sql_query("SELECT report_time, temp_c, dewp_c, wdir, wspd_kt, wgst_kt, visib_sm, ceiling_ft, "
                             "flt_cat, wx_string FROM metar_hist", conn)
    live = pd.read_sql_query("SELECT report_time, temp_c, dewp_c, wdir, wspd_kt, wgst_kt, visib, ceiling_ft, "
                             "flt_cat, wx_string FROM metar", conn)
    live["visib_sm"] = live.pop("visib").map(_parse_visib)
    m = pd.concat([hist.assign(_src=0), live.assign(_src=1)], ignore_index=True)
    m["report_time"] = pd.to_datetime(m["report_time"], utc=True, format="ISO8601").dt.floor("min")
    m = m.sort_values(["report_time", "_src"]).drop_duplicates("report_time", keep="first").drop(columns="_src")
    for c in ("temp_c", "dewp_c", "wdir", "wspd_kt", "wgst_kt", "visib_sm", "ceiling_ft"):
        m[c] = pd.to_numeric(m[c], errors="coerce")  # live table may contain "VRB" wind direction
    wx = m["wx_string"].fillna("")
    m["wx_rain"] = wx.str.contains(r"RA|DZ|SH", regex=True).astype(int)
    m["wx_ts"] = wx.str.contains("TS").astype(int)
    m["wx_fog"] = wx.str.contains(r"FG|BR", regex=True).astype(int)
    m["wgst_kt"] = m["wgst_kt"].fillna(0)
    return m.reset_index(drop=True)


def load_tc_signals(conn) -> pd.DataFrame:
    tc = pd.read_sql_query("SELECT signal, start_ts, end_ts FROM tc_signals", conn)
    tc["start_ts"] = pd.to_datetime(tc["start_ts"], utc=True)
    tc["end_ts"] = pd.to_datetime(tc["end_ts"], utc=True)
    return tc


LINK_COLS = ["date", "flight_no", "scheduled_ts", "arr_actual_ts", "confidence", "arr_sched_ts"]
LINKS_SQL = """
SELECT l.date, l.dep_flight_no AS flight_no, l.dep_scheduled_ts AS scheduled_ts,
       l.arr_actual_ts, l.confidence, a.scheduled_ts AS arr_sched_ts
FROM aircraft_links l
LEFT JOIN arrivals a ON a.date=l.arr_date AND a.flight_no=l.arr_flight_no
                    AND a.scheduled_time=l.arr_scheduled_time
WHERE l.method='stand_gate'
"""


def load_links(conn) -> pd.DataFrame:
    """Inbound-aircraft links, one row per departure — the `stand_gate` proxy only.

    `method='stand_gate'` is the only method with history over the whole backfill; `adsb_hex` links exist for a few
    hundred recent departures and are validation-only, so they are filtered out here rather than de-duplicated later
    (both methods can link the same departure, which would otherwise duplicate feature rows). The arrivals join adds
    the inbound's *scheduled* arrival time, which is immutable and therefore safe to use at any horizon.
    Empty (typed) frame when the table does not exist yet — fresh databases and test fixtures.
    """
    try:
        has = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='aircraft_links'").fetchone()
    except sqlite3.Error:
        has = None
    df = pd.read_sql_query(LINKS_SQL, conn) if has else pd.DataFrame(columns=LINK_COLS)
    for c in ("scheduled_ts", "arr_actual_ts", "arr_sched_ts"):
        df[c] = pd.to_datetime(df[c], utc=True, format="ISO8601")
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").astype(float)
    for c in ("date", "flight_no"):
        df[c] = df[c].astype(str)
    return df[LINK_COLS]


def links_event_source(conn) -> str:
    """'sched' only when the latest `rotations` run rebuilt links from scheduled departure times **over the whole
    window**, else 'actual'.

    `hkia.rotations --events sched` marks its ingest_log detail with `events=sched`, and an `--all` run adds
    `scope=all`. Both markers are required: a one-date `--events sched` run leaves the other ~90 days of
    `aircraft_links` paired on *actual* departure times, which are label-dependent, and would otherwise mark the whole
    parquet leak-free on the strength of a single day (see docs/inbound-feature.md).
    """
    try:
        row = conn.execute("SELECT detail FROM ingest_log WHERE job='rotations' ORDER BY run_at DESC LIMIT 1").fetchone()
    except sqlite3.Error:
        return "actual"
    detail = row[0] if row and row[0] else ""
    return "sched" if "events=sched" in detail and "scope=all" in detail else "actual"


# ---------- feature blocks ----------

def calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    local = df["scheduled_ts"].dt.tz_convert(HKT)
    out = pd.DataFrame(index=df.index)
    out["sched_hour"] = local.dt.hour
    out["sched_minute_of_day"] = local.dt.hour * 60 + local.dt.minute
    out["sched_dow"] = local.dt.dayofweek
    out["sched_month"] = local.dt.month
    out["is_weekend"] = (out["sched_dow"] >= 5).astype(int)
    hol = holiday_dates()
    out["is_holiday"] = local.dt.date.map(lambda d: int(d in hol))
    return out


def congestion_features(sched: pd.Series) -> pd.DataFrame:
    """Counts of scheduled departures (all rows, incl. cancelled) around each scheduled time. `sched` must be sorted."""
    t = sched.values.astype("datetime64[ns]").astype("int64")
    out = pd.DataFrame(index=sched.index)
    for name, w in (("cong_pm60", 60), ("cong_pm30", 30)):
        half = np.int64(w * 60 * 1e9)
        out[name] = np.searchsorted(t, t + half, side="right") - np.searchsorted(t, t - half, side="left") - 1
    hour = sched.dt.tz_convert(HKT).dt.floor("h")
    out["cong_same_hour"] = hour.map(hour.value_counts()) - 1
    return out


def weather_asof(df: pd.DataFrame, metar: pd.DataFrame, tolerance="3h") -> pd.DataFrame:
    """Latest METAR strictly before scheduled_ts (allow_exact_matches=False), within `tolerance`."""
    left = df[["scheduled_ts"]].reset_index()
    cols = ["temp_c", "dewp_c", "wdir", "wspd_kt", "wgst_kt", "visib_sm", "ceiling_ft", "flt_cat",
            "wx_rain", "wx_ts", "wx_fog"]
    joined = pd.merge_asof(left.sort_values("scheduled_ts"), metar[["report_time"] + cols].sort_values("report_time"),
                           left_on="scheduled_ts", right_on="report_time", direction="backward",
                           allow_exact_matches=False, tolerance=pd.Timedelta(tolerance))
    joined = joined.set_index("index").sort_index()
    joined["metar_age_min"] = (joined["scheduled_ts"] - joined["report_time"]).dt.total_seconds() / 60
    return joined[cols + ["metar_age_min"]]


def tc_features(sched: pd.Series, tc: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"tc_signal": 0, "msn_signal": 0}, index=sched.index)
    for _, r in tc.iterrows():
        active = (sched >= r["start_ts"]) & (sched < r["end_ts"])
        if not active.any():
            continue
        if r["signal"] == "MSN":
            out.loc[active, "msn_signal"] = 1
        else:
            out.loc[active, "tc_signal"] = np.maximum(out.loc[active, "tc_signal"], int(r["signal"]))
    return out


def pit_group_mean(targets: pd.DataFrame, hist: pd.DataFrame, keys: list[str], cutoff_col: str,
                   value_col: str = "delay_min", time_col: str = "actual_ts") -> tuple[pd.Series, pd.Series]:
    """Point-in-time group mean: for each target row, mean of hist[value_col] over hist rows sharing `keys`
    whose hist[time_col] < target[cutoff_col]. Returns (mean, count) aligned to targets.index."""
    mean = pd.Series(np.nan, index=targets.index)
    cnt = pd.Series(0, index=targets.index, dtype=int)
    hist = hist.dropna(subset=[time_col, value_col]).sort_values(time_col)
    groups = {k: g for k, g in hist.groupby(keys, sort=False)}
    for k, tg in targets.groupby(keys, sort=False):
        g = groups.get(k)
        if g is None:
            continue
        times = g[time_col].values.astype("datetime64[ns]")
        csum = np.concatenate([[0.0], np.cumsum(g[value_col].values)])
        n = np.searchsorted(times, tg[cutoff_col].values.astype("datetime64[ns]"), side="left")
        cnt.loc[tg.index] = n
        with np.errstate(invalid="ignore", divide="ignore"):
            mean.loc[tg.index] = np.where(n > 0, csum[n] / np.maximum(n, 1), np.nan)
    return mean, cnt


def rolling_delay_features(df: pd.DataFrame) -> pd.DataFrame:
    """Prior-day airline mean delay, same-day airline mean delay, same-day airport-wide mean delay — all
    restricted to flights whose actual_ts < scheduled_ts - 2 h (point-in-time)."""
    hist = df.loc[df["delay_min"].notna(), ["airline", "date", "actual_ts", "delay_min"]]
    t = df[["airline", "date"]].copy()
    t["cutoff"] = df["scheduled_ts"] - PIT_LAG
    t["prev_date"] = (pd.to_datetime(t["date"]) - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
    out = pd.DataFrame(index=df.index)
    h_prev = hist.rename(columns={"date": "prev_date"})
    out["airline_prevday_mean_delay"], out["airline_prevday_n"] = pit_group_mean(t, h_prev, ["airline", "prev_date"], "cutoff")
    out["airline_sameday_mean_delay"], out["airline_sameday_n"] = pit_group_mean(t, hist, ["airline", "date"], "cutoff")
    out["airport_sameday_mean_delay"], out["airport_sameday_n"] = pit_group_mean(t, hist, ["date"], "cutoff")
    return out


def inbound_features(df: pd.DataFrame, links: pd.DataFrame | None, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Turnaround block from the linked inbound aircraft — point-in-time at `scheduled_ts - PIT_LAG`.

    The inbound counts only when it was **on blocks strictly before the cutoff**; its on-blocks time is otherwise the
    future (the aircraft may land after the cutoff, or never). `now` additionally gates on the cutoff having been
    reached at all, which is what makes serving identical to training: a flight scored 5 h out gets the same all-missing
    block a flight with no link gets, because at that moment nothing about the inbound is knowable under this rule.

    Encoding: `inbound_known` is a real 0/1 (never NaN, never imputed), the four value features are NaN whenever it is 0
    and ride XGBoost's native missing branch. A link whose arrivals row is absent (`arr_sched_ts` NaT) still yields
    `inbound_known` and `inbound_actual_slack_min`; the two scheduled-arrival features stay NaN.
    """
    keys = ["date", "flight_no", "scheduled_ts"]
    if links is None or not len(links):
        nat = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")   # tz-aware: compared against a UTC cutoff
        m = pd.DataFrame({"arr_actual_ts": nat, "arr_sched_ts": nat, "confidence": np.nan}, index=df.index)
    else:
        m = df[keys].merge(links[LINK_COLS], on=keys, how="left", validate="one_to_one")
        assert len(m) == len(df), f"inbound link merge changed the row count: {len(df)} -> {len(m)}"
        m.index = df.index

    cutoff = df["scheduled_ts"] - PIT_LAG
    known = m["arr_actual_ts"].notna() & (m["arr_actual_ts"] < cutoff)
    if now is not None:
        known &= cutoff <= pd.Timestamp(now)
    minutes = lambda a, b: (a - b).dt.total_seconds() / 60  # noqa: E731 - signed gap in minutes
    out = pd.DataFrame(index=df.index)
    out["inbound_known"] = known.astype(int)
    out["inbound_actual_slack_min"] = minutes(df["scheduled_ts"], m["arr_actual_ts"]).where(known)
    out["inbound_lateness_min"] = minutes(m["arr_actual_ts"], m["arr_sched_ts"]).where(known)
    out["inbound_sched_slack_min"] = minutes(df["scheduled_ts"], m["arr_sched_ts"]).where(known)
    out["inbound_confidence"] = m["confidence"].where(known)
    return out


# ---------- assembly ----------

def build_features(flights: pd.DataFrame, metar: pd.DataFrame, tc: pd.DataFrame,
                   top_dest_n: int = TOP_DEST_N, top_dest: set | None = None,
                   keep_unlabelled: bool = False, links: pd.DataFrame | None = None,
                   now: pd.Timestamp | None = None) -> tuple[pd.DataFrame, dict]:
    """Shared by training (`hkia.features`) and inference (`hkia.predict`).

    top_dest: explicit set of destinations kept as their own category (inference passes the training set so the
              `dest` encoding matches the model); default = top `top_dest_n` by frequency in `flights`.
    keep_unlabelled: keep rows without a label (not-yet-departed / blank status) — needed for inference; training drops them.
    links: `load_links(conn)` output for the inbound block; None (the default) yields the same all-missing block an
           unlinked flight gets, so every caller keeps working without an `aircraft_links` table.
    now: scoring time (tz-aware UTC). Only inbound state whose cutoff has been reached by `now` is used — see
         `inbound_features`. None = training mode (no serve-time gate).
    """
    df = flights.copy()
    df["delay_min"] = (df["actual_ts"] - df["scheduled_ts"]).dt.total_seconds() / 60
    outlier = df["delay_min"].notna() & ((df["delay_min"] < DELAY_MIN) | (df["delay_min"] > DELAY_MAX))
    stats = {"n_input": len(df), "n_outliers_dropped": int(outlier.sum()),
             "n_outlier_low": int((df["delay_min"] < DELAY_MIN).sum()), "n_outlier_high": int((df["delay_min"] > DELAY_MAX).sum())}
    df.loc[outlier, "delay_min"] = np.nan  # outliers do not feed the rolling features either

    # congestion uses every scheduled row (incl. cancelled/unlabelled) — the schedule is known in advance
    cong = congestion_features(df["scheduled_ts"])
    cal = calendar_features(df)
    wx = weather_asof(df, metar)
    tcf = tc_features(df["scheduled_ts"], tc)
    roll = rolling_delay_features(df)
    inb = inbound_features(df, links, now)

    first_dest = df["destination"].fillna("").str.split(",").str[0]
    top = set(top_dest) if top_dest is not None else set(first_dest.value_counts().head(top_dest_n).index)
    base = pd.DataFrame({
        "date": df["date"], "flight_no": df["flight_no"], "scheduled_ts": df["scheduled_ts"], "actual_ts": df["actual_ts"],
        "airline": df["airline"].fillna("UNK"),
        "dest": first_dest.where(first_dest.isin(top), "OTHER"),
        "dest_region": df["destination"].map(region_of),
        "terminal": df["terminal"].fillna("UNK"),
        "n_dest_legs": df["destination"].fillna("").str.count(",") + 1,
        "cancelled": df["cancelled"], "delay_min": df["delay_min"],
    }, index=df.index)
    feat = pd.concat([base, cal, cong, wx, tcf, roll, inb], axis=1)
    feat["delayed15"] = (feat["delay_min"] > 15).astype("float").where(feat["delay_min"].notna())
    feat["flt_cat"] = feat["flt_cat"].fillna("UNK")

    keep = (feat["delay_min"].notna()) | (feat["cancelled"] == 1)
    stats["n_unlabelled_dropped"] = int((~keep & ~outlier).sum())
    if keep_unlabelled:
        keep = ~outlier
        stats["n_unlabelled_dropped"] = 0
    feat = feat.loc[keep].reset_index(drop=True)
    stats.update(n_rows=len(feat), n_departed=int((feat["cancelled"] == 0).sum()), n_cancelled=int(feat["cancelled"].sum()),
                 date_min=feat["date"].min(), date_max=feat["date"].max(),
                 weather_coverage=float(feat["temp_c"].notna().mean()),
                 inbound_known_rate=float(feat["inbound_known"].mean()) if len(feat) else 0.0)
    return feat, stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "data" / "features.parquet"))
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    conn = connect()
    flights, metar, tc = load_flights(conn), load_metar(conn), load_tc_signals(conn)
    links, src = load_links(conn), links_event_source(conn)
    log.info("flights %d, metar obs %d (%s..%s), tc rows %d, inbound links %d (events=%s)", len(flights), len(metar),
             metar["report_time"].min(), metar["report_time"].max(), len(tc), len(links), src)
    feat, stats = build_features(flights, metar, tc, links=links)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    feat.to_parquet(a.out, index=False)
    # the parquet alone cannot say whether its links were rebuilt leak-free; the gate reads this instead
    meta = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "rows": int(len(feat)),
            "links_event_source": src, "inbound_known_rate": round(stats["inbound_known_rate"], 4)}
    Path(a.out).with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    log.info("wrote %s: %s (meta %s)", a.out, stats, meta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
