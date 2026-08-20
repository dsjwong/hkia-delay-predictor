"""hkia.export_json against the synthetic fixture db of test_api (no network; models/ + reports/ of the repo are read if present)."""
import json

from hkia import export_json as E
from tests.test_api import DAY, NOW, fixture_db  # noqa: F401  (fixture re-exported)


def test_export_writes_all_files(fixture_db, tmp_path):
    out = tmp_path / "data"
    sizes = E.export(fixture_db, out, now=NOW)
    assert set(sizes) == {"meta.json", "departures_yesterday.json", "departures_today.json", "departures_tomorrow.json",
                          "patterns.json", "model.json", "weather.json"}
    assert sum(sizes.values()) < 1_000_000
    meta = json.loads((out / "meta.json").read_text())
    assert meta["dates"]["today"] == DAY and meta["counts"]["today_flights"] == 150 and meta["counts"]["predictions"] == 300
    assert meta["iata_to_icao"]["CX"] == "CPA" and meta["airports"]["TPE"]["city"].startswith("Taipei")
    today = json.loads((out / "departures_today.json").read_text())
    f = today["flights"][0]
    assert f["status"] == "departed" and f["delay_min"] is not None and f["p"] != 0.5  # latest score, not the early one
    assert f["history"][0][0] < f["history"][-1][0] and f["sched_ts"].endswith("Z")
    assert today["flights"][-1]["status"] == "scheduled" and "delay_min" in today["flights"][-1]
    # "why this prediction": top-3 attributions, only on flights that have not departed yet
    assert "why" not in f, "departed flights carry their score but not the attribution block"
    why = today["flights"][-1]["why"]
    assert len(why) == 3 and [w[0] for w in why] == [1, 1, -1]           # [direction, one-liner, probability points]
    assert why[0][1] == "thunderstorm reported at the field" and why[2][1].startswith("operated by Cathay")
    assert abs(why[0][2]) > abs(why[2][2]) > 0                           # ranked by size, signed like the direction
    assert sum(1 for x in today["flights"] if "why" in x) == 30          # the 30 still-scheduled flights
    pat = json.loads((out / "patterns.json").read_text())
    assert pat["summary"]["n"] == 120 and len(pat["heatmap"]["mean_delay"]) == 7 and len(pat["heatmap"]["mean_delay"][0]) == 24
    assert pat["airlines"][0]["code"] == "CPA" and pat["destinations"][0]["code"] == "TPE"
    wx = json.loads((out / "weather.json").read_text())
    assert wx["metar"]["flt_cat"] == "VFR" and wx["hko_warnings"][0]["code"] == "WHOT"
    model = json.loads((out / "model.json").read_text())
    assert "live_eval" in model and model["live_eval"]["n_matured"] == 120 and len(model["limitations"]) >= 4
    ev = model["live_eval"]  # the report-card slices ride along in model.json (kept small: the whole file is < 100 KB)
    assert sizes["model.json"] < 100_000
    assert {"daily", "lead_buckets", "calibration", "notable", "deltas"} <= set(ev)
    assert sum(r["n"] for r in ev["daily"]) == ev["n_matured"] == sum(b["n"] for b in ev["lead_buckets"])
    assert len(ev["notable"]["confident_correct"]) == 5 and len(ev["notable"]["worst_misses"]) == 5
