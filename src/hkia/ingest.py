"""Run all ingestion jobs: `python -m hkia.ingest [--backfill]`. Idempotent."""
import argparse
import logging
import sys

from . import ingest_flights, ingest_weather


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true", help="flights: ingest whole ~91-day window")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    rc = ingest_flights.main(["--backfill"] if a.backfill else [])
    rc |= ingest_weather.main([])
    return rc


if __name__ == "__main__":
    sys.exit(main())
