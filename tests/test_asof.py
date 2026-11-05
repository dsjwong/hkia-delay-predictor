import pandas as pd
import pytest

from hkia import asof
from test_features import EMPTY_TC, _flights, _metar


def test_day_ahead_time_is_noon_hkt_the_day_before():
    t = asof.day_ahead_times(["2026-11-03"])["2026-11-03"]
    assert t == pd.Timestamp("2026-11-02T04:00:00Z")


def test_recent_complete_dates_skips_unfinished_days_and_honours_after():
    fl = _flights([("A1", "CPA", "2026-06-01T02:00:00Z", "2026-06-01T02:05:00Z", "Dep"),
                   ("A2", "CPA", "2026-06-02T02:00:00Z", "2026-06-02T02:05:00Z", "Dep"),
                   ("A3", "CPA", "2026-06-03T02:00:00Z", None, "Scheduled"),
                   ("A4", "CPA", "2026-06-04T02:00:00Z", None, "Cancelled")])
    assert asof.recent_complete_dates(fl, 7) == ["2026-06-01", "2026-06-02"]
    assert asof.recent_complete_dates(fl, 7, after="2026-06-01") == ["2026-06-02"]
    assert asof.recent_complete_dates(fl, 1) == ["2026-06-02"]


def test_asof_frame_never_sees_actuals_or_weather_after_the_scoring_time():
    pytest.importorskip("xgboost")
    fl = _flights([("A1", "CPA", "2026-06-01T01:00:00Z", "2026-06-01T01:50:00Z", "Dep"),   # left late, before T
                   ("A2", "CPA", "2026-06-01T06:00:00Z", "2026-06-01T06:40:00Z", "Dep"),   # target; actual is after T
                   ("A3", "CPA", "2026-06-01T09:00:00Z", "2026-06-01T10:00:00Z", "Dep")])
    now = pd.Timestamp("2026-06-01T04:00:00Z")
    m = _metar(["2026-06-01T03:00:00Z", "2026-06-01T05:00:00Z"])
    m["temp_c"] = [20.0, 99.0]
    inp = asof.Inputs(fl, m, EMPTY_TC, pd.DataFrame(columns=["date", "flight_no", "scheduled_ts", "arr_actual_ts",
                                                            "confidence", "arr_sched_ts"]))
    feat = asof.asof_frame(inp, now, ["2026-06-01"], {"TPE"}).set_index("flight_no")
    assert feat["actual_ts"].isna().loc[["A2", "A3"]].all() and feat["delay_min"].isna().loc[["A2", "A3"]].all()
    assert (feat.loc[["A2", "A3"], "temp_c"] == 20.0).all()          # the 05:00 observation (99) is in the future
    assert feat.loc["A3", "airport_sameday_n"] == 1                  # only A1; A2's 06:40 departure is after T, blanked
