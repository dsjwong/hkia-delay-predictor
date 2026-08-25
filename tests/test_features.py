import datetime as dt
import sqlite3

import numpy as np
import pandas as pd
import pytest

from hkia import features as F
from hkia.backfill_weather import flight_category, parse_iem_csv, parse_tc_dat
from hkia.holidays import is_holiday

UTC = dt.timezone.utc


def _flights(rows):
    """rows: (flight_no, airline, scheduled UTC iso, actual UTC iso | None, status)"""
    df = pd.DataFrame(rows, columns=["flight_no", "airline", "scheduled_ts", "actual_ts", "status_raw"])
    df["scheduled_ts"] = pd.to_datetime(df["scheduled_ts"], utc=True)
    df["actual_ts"] = pd.to_datetime(df["actual_ts"], utc=True)
    df["date"] = df["scheduled_ts"].dt.tz_convert(F.HKT).dt.strftime("%Y-%m-%d")
    df["destination"], df["terminal"] = "TPE", "T1"
    df["cancelled"] = (df["status_raw"] == "Cancelled").astype(int)
    return df.sort_values("scheduled_ts").reset_index(drop=True)


def _metar(times, **cols):
    m = pd.DataFrame({"report_time": pd.to_datetime(times, utc=True)})
    for c in ("temp_c", "dewp_c", "wdir", "wspd_kt", "wgst_kt", "visib_sm", "ceiling_ft", "wx_rain", "wx_ts", "wx_fog"):
        m[c] = cols.get(c, 0.0)
    m["flt_cat"] = "VFR"
    return m


EMPTY_TC = pd.DataFrame({"signal": pd.Series(dtype=str), "start_ts": pd.Series(dtype="datetime64[ns, UTC]"),
                         "end_ts": pd.Series(dtype="datetime64[ns, UTC]")})


def test_congestion_counts_synthetic_day():
    # three flights at 10:00, 10:30, 12:00 (HKT): +-60 min window counts *other* flights
    fl = _flights([("A1", "CPA", "2026-06-01T02:00:00Z", "2026-06-01T02:05:00Z", "Dep"),
                   ("A2", "CPA", "2026-06-01T02:30:00Z", "2026-06-01T02:30:00Z", "Dep"),
                   ("A3", "HDA", "2026-06-01T04:00:00Z", "2026-06-01T04:40:00Z", "Dep")])
    cong = F.congestion_features(fl["scheduled_ts"])
    assert cong["cong_pm60"].tolist() == [1, 1, 0]
    assert cong["cong_pm30"].tolist() == [1, 1, 0]
    assert cong["cong_same_hour"].tolist() == [1, 1, 0]


def test_no_nan_labels_and_outliers_dropped():
    fl = _flights([("A1", "CPA", "2026-06-01T02:00:00Z", "2026-06-01T02:20:00Z", "Dep"),      # +20 -> delayed15
                   ("A2", "CPA", "2026-06-01T03:00:00Z", "2026-06-01T02:50:00Z", "Dep"),      # -10
                   ("A3", "CPA", "2026-06-01T04:00:00Z", "2026-06-01T15:00:00Z", "Dep"),      # +660 -> outlier
                   ("A4", "CPA", "2026-06-01T05:00:00Z", None, "Cancelled"),
                   ("A5", "CPA", "2026-06-01T06:00:00Z", None, "")])                          # unlabelled
    metar = _metar(["2026-06-01T01:00:00Z"])
    feat, stats = F.build_features(fl, metar, EMPTY_TC)
    departed = feat[feat["cancelled"] == 0]
    assert departed["delay_min"].notna().all() and departed["delayed15"].notna().all()
    assert departed["delayed15"].tolist() == [1.0, 0.0]
    assert stats["n_outliers_dropped"] == 1 and stats["n_unlabelled_dropped"] == 1
    assert feat["cancelled"].sum() == 1 and len(feat) == 3


def test_weather_asof_strictly_before():
    fl = _flights([("A1", "CPA", "2026-06-01T02:00:00Z", "2026-06-01T02:00:00Z", "Dep")])
    metar = _metar(["2026-06-01T01:00:00Z", "2026-06-01T02:00:00Z", "2026-06-01T03:00:00Z"], temp_c=[10.0, 20.0, 30.0])
    wx = F.weather_asof(fl, metar)
    assert wx.loc[0, "temp_c"] == 10.0          # obs at exactly scheduled time is NOT used, later obs never
    assert wx.loc[0, "metar_age_min"] == 60
    far = _metar(["2026-06-01T00:00:00Z"] , temp_c=[5.0])   # older than tolerance (3h)? no: 2h -> used
    assert F.weather_asof(fl, far).loc[0, "temp_c"] == 5.0
    too_old = _metar(["2026-05-31T20:00:00Z"], temp_c=[5.0])
    assert np.isnan(F.weather_asof(fl, too_old).loc[0, "temp_c"])


def test_point_in_time_rolling_ignores_future_rows():
    # target flight X scheduled 12:00Z; cutoff = 10:00Z. Same airline, same day:
    #  H1 actual 09:00Z (delay 60)  -> counts
    #  H2 actual 10:00Z (delay 0)   -> NOT counts (must be strictly before cutoff)
    #  H3 actual 11:30Z (delay 200) -> future w.r.t. cutoff, NOT counts (would leak)
    #  P1 previous day, actual 05:00Z prev day (delay 30) -> prevday counts
    #  P2 previous day scheduled 23:30Z-ish... actual after cutoff -> NOT counts
    fl = _flights([("P1", "CPA", "2026-05-31T05:00:00Z", "2026-05-31T05:30:00Z", "Dep"),
                   ("P2", "CPA", "2026-05-31T15:00:00Z", "2026-06-01T11:00:00Z", "Dep"),  # +1200 min -> outlier (NaN label), ignored
                   ("H1", "CPA", "2026-06-01T08:00:00Z", "2026-06-01T09:00:00Z", "Dep"),
                   ("H2", "CPA", "2026-06-01T10:00:00Z", "2026-06-01T10:00:00Z", "Dep"),
                   ("H3", "CPA", "2026-06-01T08:10:00Z", "2026-06-01T11:30:00Z", "Dep"),
                   ("Z1", "HDA", "2026-06-01T09:00:00Z", "2026-06-01T09:10:00Z", "Dep"),
                   ("X", "CPA", "2026-06-01T12:00:00Z", "2026-06-01T12:00:00Z", "Dep")])
    df = fl.copy()
    df["delay_min"] = (df["actual_ts"] - df["scheduled_ts"]).dt.total_seconds() / 60
    df.loc[df["delay_min"] > 600, "delay_min"] = np.nan
    roll = F.rolling_delay_features(df)
    x = roll.loc[df["flight_no"] == "X"].iloc[0]
    assert x["airline_sameday_n"] == 1 and x["airline_sameday_mean_delay"] == 60
    assert x["airline_prevday_n"] == 1 and x["airline_prevday_mean_delay"] == 30
    assert x["airport_sameday_n"] == 2 and x["airport_sameday_mean_delay"] == pytest.approx(35)  # H1 (60) + Z1 (10)
    # a flight with nothing before its cutoff gets NaN mean and 0 count (never a peek at later rows)
    p1 = roll.loc[df["flight_no"] == "P1"].iloc[0]
    assert p1["airline_sameday_n"] == 0 and np.isnan(p1["airline_sameday_mean_delay"])
    # brute-force cross-check for every row: recompute with an explicit filter
    for i, r in df.iterrows():
        cutoff = r["scheduled_ts"] - F.PIT_LAG
        h = df[(df["airline"] == r["airline"]) & (df["date"] == r["date"]) & (df["actual_ts"] < cutoff) & df["delay_min"].notna()]
        assert roll.loc[i, "airline_sameday_n"] == len(h)
        if len(h):
            assert roll.loc[i, "airline_sameday_mean_delay"] == pytest.approx(h["delay_min"].mean())


def _links(rows):
    """rows: (flight_no, dep scheduled UTC iso, inbound on-blocks UTC iso | None, inbound scheduled UTC iso | None, conf)"""
    df = pd.DataFrame(rows, columns=["flight_no", "scheduled_ts", "arr_actual_ts", "arr_sched_ts", "confidence"])
    for c in ("scheduled_ts", "arr_actual_ts", "arr_sched_ts"):
        df[c] = pd.to_datetime(df[c], utc=True)
    df["date"] = df["scheduled_ts"].dt.tz_convert(F.HKT).dt.strftime("%Y-%m-%d")
    return df[F.LINK_COLS]


# every departure below is scheduled 12:00Z, so the point-in-time cutoff is 10:00Z
INBOUND_FLIGHTS = [("L1", "CPA", "2026-06-01T12:00:00Z", "2026-06-01T12:00:00Z", "Dep"),   # inbound on blocks 09:00Z
                   ("L2", "CPA", "2026-06-01T12:00:00Z", "2026-06-01T12:00:00Z", "Dep"),   # on blocks 11:00Z (too late)
                   ("L3", "CPA", "2026-06-01T12:00:00Z", "2026-06-01T12:00:00Z", "Dep"),   # linked, never on blocks
                   ("L4", "CPA", "2026-06-01T12:00:00Z", "2026-06-01T12:00:00Z", "Dep"),   # no link at all
                   ("L5", "CPA", "2026-06-01T12:00:00Z", "2026-06-01T12:00:00Z", "Dep")]   # link, arrivals row missing
INBOUND_LINKS = [("L1", "2026-06-01T12:00:00Z", "2026-06-01T09:00:00Z", "2026-06-01T08:30:00Z", 1.0),
                 ("L2", "2026-06-01T12:00:00Z", "2026-06-01T11:00:00Z", "2026-06-01T10:45:00Z", 1.0),
                 ("L3", "2026-06-01T12:00:00Z", None, "2026-06-01T09:00:00Z", 0.6),
                 ("L5", "2026-06-01T12:00:00Z", "2026-06-01T09:00:00Z", None, 0.6)]
VALUE_COLS = ["inbound_actual_slack_min", "inbound_lateness_min", "inbound_sched_slack_min", "inbound_confidence"]


def _inbound(now=None):
    fl = _flights(INBOUND_FLIGHTS)
    out = F.inbound_features(fl, _links(INBOUND_LINKS), now=now)
    out.index = fl["flight_no"]
    return out


def test_inbound_features_only_count_an_inbound_on_stand_before_the_cutoff():
    inb = _inbound()
    assert inb["inbound_known"].tolist() == [1, 0, 0, 0, 1]      # L2 landed after the cutoff -> not knowable
    l1 = inb.loc["L1"]
    assert l1["inbound_actual_slack_min"] == 180 and l1["inbound_lateness_min"] == 30
    assert l1["inbound_sched_slack_min"] == 210 and l1["inbound_confidence"] == 1.0
    # the three unknown rows are byte-identical: landed inside the cutoff window, never landed, and never linked all
    # collapse to the same encoding, because at the cutoff the model knew the same thing about all three (nothing)
    for fn in ("L2", "L3", "L4"):
        assert inb.loc[fn, "inbound_known"] == 0
        assert inb.loc[fn, VALUE_COLS].isna().all(), fn
    # a link whose arrivals row is missing still knows the turnaround, not the inbound's schedule
    l5 = inb.loc["L5"]
    assert l5["inbound_actual_slack_min"] == 180 and l5["inbound_confidence"] == 0.6
    assert np.isnan(l5["inbound_lateness_min"]) and np.isnan(l5["inbound_sched_slack_min"])
    assert inb["inbound_known"].notna().all() and inb["inbound_known"].isin((0, 1)).all()


def test_inbound_now_gate_makes_serving_identical_to_training():
    train = _inbound()
    # scored 3 h before departure: the cutoff (s-2h) has not been reached, so nothing is knowable yet
    early = _inbound(now=pd.Timestamp("2026-06-01T09:00:00Z"))
    assert early["inbound_known"].tolist() == [0] * 5
    assert early[VALUE_COLS].isna().all().all()
    # scored 1 h before departure: the cutoff has passed, and the block equals what training built for the same rows
    late = _inbound(now=pd.Timestamp("2026-06-01T11:00:00Z"))
    pd.testing.assert_frame_equal(late, train)


def test_inbound_features_without_links_are_the_all_missing_block():
    fl = _flights(INBOUND_FLIGHTS)
    for links in (None, _links([]).iloc[:0]):
        inb = F.inbound_features(fl, links)
        assert list(inb.columns) == F.INBOUND and inb["inbound_known"].tolist() == [0] * len(fl)
        assert inb[VALUE_COLS].isna().all().all()


def test_inbound_features_brute_force_cross_check():
    fl = _flights([("A1", "CPA", "2026-06-01T02:00:00Z", "2026-06-01T02:05:00Z", "Dep"),
                   ("A2", "CPA", "2026-06-01T06:00:00Z", "2026-06-01T06:30:00Z", "Dep"),
                   ("A3", "HDA", "2026-06-01T09:00:00Z", None, ""),
                   ("A4", "HDA", "2026-06-01T18:00:00Z", "2026-06-01T18:20:00Z", "Dep")])
    links = _links([("A1", "2026-06-01T02:00:00Z", "2026-06-01T00:30:00Z", "2026-06-01T00:00:00Z", 1.0),
                    ("A2", "2026-06-01T06:00:00Z", "2026-06-01T03:00:00Z", "2026-06-01T03:20:00Z", 0.6),
                    ("A3", "2026-06-01T09:00:00Z", "2026-06-01T08:30:00Z", "2026-06-01T08:00:00Z", 1.0),
                    ("A4", "2026-06-01T18:00:00Z", None, "2026-06-01T15:00:00Z", 1.0)])
    by_no = {r.flight_no: r for r in links.itertuples(index=False)}
    for now in (None, pd.Timestamp("2026-06-01T07:00:00Z")):
        inb = F.inbound_features(fl, links, now=now)
        for i, r in fl.iterrows():
            cutoff = r["scheduled_ts"] - F.PIT_LAG
            lk = by_no.get(r["flight_no"])
            known = lk is not None and pd.notna(lk.arr_actual_ts) and lk.arr_actual_ts < cutoff
            if now is not None:
                known = known and cutoff <= now
            assert inb.loc[i, "inbound_known"] == int(known), (r["flight_no"], now)
            if not known:
                assert inb.loc[i, VALUE_COLS].isna().all()
                continue
            assert inb.loc[i, "inbound_actual_slack_min"] == pytest.approx(
                (r["scheduled_ts"] - lk.arr_actual_ts).total_seconds() / 60)
            assert inb.loc[i, "inbound_lateness_min"] == pytest.approx(
                (lk.arr_actual_ts - lk.arr_sched_ts).total_seconds() / 60)
            assert inb.loc[i, "inbound_confidence"] == lk.confidence


def test_build_features_inbound_block_is_optional_and_reported():
    fl = _flights([("L1", "CPA", "2026-06-01T12:00:00Z", "2026-06-01T12:10:00Z", "Dep"),
                   ("L4", "CPA", "2026-06-01T12:00:00Z", "2026-06-01T12:10:00Z", "Dep")])
    metar = _metar(["2026-06-01T11:00:00Z"])
    feat, stats = F.build_features(fl, metar, EMPTY_TC)                        # no links -> nothing breaks
    assert set(F.INBOUND) <= set(feat.columns) and stats["inbound_known_rate"] == 0.0
    feat, stats = F.build_features(fl, metar, EMPTY_TC, links=_links(INBOUND_LINKS[:1]))
    assert feat.loc[feat["flight_no"] == "L1", "inbound_known"].iloc[0] == 1
    assert stats["inbound_known_rate"] == 0.5
    assert F.FEATURES[-5:] == F.INBOUND and len(F.FEATURES) == 38


LINKS_DDL = """
CREATE TABLE aircraft_links (date TEXT, dep_flight_no TEXT, dep_scheduled_time TEXT, method TEXT, arr_date TEXT,
  arr_flight_no TEXT, arr_scheduled_time TEXT, arr_actual_ts TEXT, dep_scheduled_ts TEXT, confidence REAL);
CREATE TABLE arrivals (date TEXT, flight_no TEXT, scheduled_time TEXT, scheduled_ts TEXT);
"""


def _links_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(LINKS_DDL)
    conn.executemany("INSERT INTO aircraft_links VALUES (?,?,?,?,?,?,?,?,?,?)", [
        # the SAME departure is linked by both methods -- adsb_hex must not produce a second feature row
        ("2026-06-01", "CX 255", "20:00", "stand_gate", "2026-06-01", "CX 254", "17:00",
         "2026-06-01T17:20:00+08:00", "2026-06-01T20:00:00+08:00", 0.6),
        ("2026-06-01", "CX 255", "20:00", "adsb_hex", "2026-06-01", "CX 254", "17:00",
         "2026-06-01T17:20:00+08:00", "2026-06-01T20:00:00+08:00", 1.0),
        ("2026-06-01", "UO 674", "09:10", "stand_gate", "2026-06-01", "UO 673", "06:00",
         "2026-06-01T05:36:00+08:00", "2026-06-01T09:10:00+08:00", 1.0)])
    conn.execute("INSERT INTO arrivals VALUES ('2026-06-01','CX 254','17:00','2026-06-01T17:00:00+08:00')")
    return conn


def test_load_links_is_one_row_per_departure_and_ignores_adsb_hex():
    links = F.load_links(_links_db())
    assert list(links.columns) == F.LINK_COLS
    assert not links.duplicated(["date", "flight_no", "scheduled_ts"]).any()
    assert links["flight_no"].tolist() == ["CX 255", "UO 674"]
    cx = links[links["flight_no"] == "CX 255"].iloc[0]
    assert cx["confidence"] == 0.6                                    # the stand_gate row, not the adsb_hex one
    assert cx["arr_sched_ts"] == pd.Timestamp("2026-06-01T09:00:00Z")  # 17:00 +08:00
    assert pd.isna(links[links["flight_no"] == "UO 674"].iloc[0]["arr_sched_ts"])   # no arrivals row -> NaT, not a drop


def test_load_links_survives_a_database_without_the_table():
    links = F.load_links(sqlite3.connect(":memory:"))
    assert list(links.columns) == F.LINK_COLS and links.empty
    assert isinstance(links["scheduled_ts"].dtype, pd.DatetimeTZDtype) and links["confidence"].dtype == float
    fl = _flights(INBOUND_FLIGHTS)
    assert F.inbound_features(fl, links)["inbound_known"].tolist() == [0] * len(fl)


def test_links_event_source_needs_both_a_sched_and_a_whole_window_rebuild():
    conn = sqlite3.connect(":memory:")
    log = "INSERT INTO ingest_log VALUES (?,'rotations',?)"
    assert F.links_event_source(conn) == "actual"                     # no ingest_log at all
    conn.execute("CREATE TABLE ingest_log (run_at TEXT, job TEXT, detail TEXT)")
    assert F.links_event_source(conn) == "actual"
    # a one-date --events sched run leaves the other ~90 days paired on actual departure times: not leak-free
    conn.execute(log, ("2026-06-01T00:00:00+00:00", "2 dates, 537 linked, events=sched"))
    assert F.links_event_source(conn) == "actual"
    conn.execute(log, ("2026-06-02T00:00:00+00:00", "92 dates, 32k linked, events=sched, scope=all"))
    assert F.links_event_source(conn) == "sched"
    conn.execute(log, ("2026-06-03T00:00:00+00:00", "92 dates, 32k linked, scope=all"))
    assert F.links_event_source(conn) == "actual"                     # whole window, but paired on actual times
    conn.execute(log, ("2026-06-04T00:00:00+00:00", "2 dates, 537/905 departures linked"))
    assert F.links_event_source(conn) == "actual"                     # the LATEST run is what the parquet was built on


def test_tc_signal_active_window():
    fl = _flights([("A1", "CPA", "2026-07-25T14:00:00Z", "2026-07-25T14:00:00Z", "Dep"),
                   ("A2", "CPA", "2026-07-27T00:00:00Z", "2026-07-27T00:00:00Z", "Dep")])
    tc = pd.DataFrame({"signal": ["8", "MSN"], "start_ts": pd.to_datetime(["2026-07-25T14:10:00Z", "2026-07-25T00:00:00Z"], utc=True),
                       "end_ts": pd.to_datetime(["2026-07-25T17:10:00Z", "2026-07-26T00:00:00Z"], utc=True)})
    out = F.tc_features(fl["scheduled_ts"], tc)
    assert out.loc[0, "tc_signal"] == 0 and out.loc[0, "msn_signal"] == 1 and out.loc[1, "tc_signal"] == 0
    tc.loc[0, "start_ts"] = pd.Timestamp("2026-07-25T13:00:00Z")
    assert F.tc_features(fl["scheduled_ts"], tc).loc[0, "tc_signal"] == 8


def test_parsers_and_helpers():
    csv = ("station,valid,tmpf,dwpf,relh,drct,sknt,p01i,alti,mslp,vsby,gust,skyc1,skyc2,skyc3,skyc4,skyl1,skyl2,skyl3,skyl4,"
           "wxcodes,ice_accretion_1hr,ice_accretion_3hr,ice_accretion_6hr,peak_wind_gust,peak_wind_drct,peak_wind_time,feel,metar,snowdepth\n"
           "VHHH,2026-05-15 01:00,82.40,75.20,78.96,110.00,10.00,0.00,29.74,M,6.21,M,FEW,BKN,SCT,M,1000.00,1500.00,1800.00,M,"
           "VCTS -SHRA,M,M,M,M,M,M,89.49,VHHH 150100Z ...,M\n")
    (row,) = parse_iem_csv(csv, "now")
    assert row[0] == "2026-05-15T01:00:00Z" and row[2] == 28.0 and row[5] == 10 and row[6] is None
    assert row[7] == 6.21 and row[8] == 1500 and row[9] == "MVFR" and row[10] == "VCTS -SHRA"
    assert flight_category(6.21, None) == "VFR" and flight_category(0.5, None) == "LIFR" and flight_category(6, 900) == "IFR"
    tc = parse_tc_dat("202602\tST\tNOUL\t8\tNW\t2210\t25\t7\t2026\tX\t110\t26\t7\t2026\tX\t0300\n0\tMSN\tX\t0\tSW\t1245\t14\t6\t2026\tX\t1615\t14\t6\t2026\tX\t0330\n")
    assert tc[0][2] == "8" and tc[0][4] == "2026-07-25T22:10:00+08:00" and tc[0][5] == "2026-07-26T01:10:00+08:00"
    assert tc[1][2] == "MSN" and tc[1][4] == "2026-06-14T12:45:00+08:00"
    assert is_holiday(dt.date(2026, 7, 1)) and not is_holiday(dt.date(2026, 7, 2))
