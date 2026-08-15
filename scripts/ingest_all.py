#!/usr/bin/env python
"""Thin wrapper so `python scripts/ingest_all.py [--backfill]` works without installing the package."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hkia.ingest import main  # noqa: E402

sys.exit(main())
