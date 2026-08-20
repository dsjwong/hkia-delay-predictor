"""Shared test setup: the Streamlit AppTest suite reads whatever data/hkia.db is on disk; never download it in tests."""
import os

os.environ.setdefault("HKIA_DB_SYNC", "0")
