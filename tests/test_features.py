import datetime as dt

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
