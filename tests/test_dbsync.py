"""hkia.dbsync: the release-hosted database. Network is monkeypatched; `gh` is never called."""
import json
import sqlite3
from pathlib import Path

import pytest

from hkia import db as _db
from hkia import dbsync


def make_db(path: Path, n_flights: int) -> Path:
    with sqlite3.connect(path) as c:
        c.executescript(_db.SCHEMA)
        c.executemany(
            "INSERT INTO flights (date, flight_no, scheduled_time, scheduled_ts, first_seen_at, fetched_at) VALUES (?,?,?,?,?,?)",
            [("2026-08-01", f"CX {i}", "10:00", "2026-08-01T10:00+08:00", "x", "x") for i in range(n_flights)])
    return path


class FakeRemote:
    """Stands in for the release: serves meta + db bytes via dbsync._fetch."""

    def __init__(self, db: Path | None):
        self.db = db
        self.meta = dbsync.build_meta(db) if db else None
        self.downloads = 0

    def fetch(self, url, dest=None, timeout=0):
        if url.endswith(dbsync.META_ASSET):
            return json.dumps(self.meta).encode() if self.meta else None
        if url.endswith(dbsync.ASSET):
            if self.db is None:
                return None
            self.downloads += 1
            dest.write_bytes(self.db.read_bytes())
            return b""
        raise AssertionError(url)


@pytest.fixture
def remote(tmp_path, monkeypatch):
    r = FakeRemote(make_db(tmp_path / "remote.db", 20))
    monkeypatch.setattr(dbsync, "_fetch", r.fetch)
    return r


def test_pull_downloads_verifies_and_writes_sidecar(tmp_path, remote):
    dest = tmp_path / "data" / "hkia.db"
    msg = dbsync.pull(dest)
    assert msg.startswith("downloaded") and dest.exists()
    assert json.loads(dbsync.sidecar(dest).read_text())["sha256"] == remote.meta["sha256"]
    assert dbsync.row_counts(dest)["flights"] == 20
    assert not (tmp_path / "data" / "hkia.db.part").exists()


def test_pull_skips_download_when_current(tmp_path, remote):
    dest = tmp_path / "hkia.db"
    dbsync.pull(dest)
    assert remote.downloads == 1
    assert dbsync.pull(dest).startswith("current")
    assert remote.downloads == 1
    assert dbsync.pull(dest, force=True).startswith("downloaded")
    assert remote.downloads == 2


def test_pull_keeps_local_copy_on_checksum_mismatch(tmp_path, remote):
    dest = tmp_path / "hkia.db"
    dbsync.pull(dest)
    before = dest.read_bytes()
    remote.meta = dict(remote.meta, sha256="0" * 64, uploaded_at="later")   # sidecar updated, db not yet (mid-upload)
    assert "mismatch" in dbsync.pull(dest)
    assert dest.read_bytes() == before


def test_pull_with_no_remote_and_no_local_fails_loudly(tmp_path, monkeypatch):
    monkeypatch.setattr(dbsync, "_fetch", FakeRemote(None).fetch)
    with pytest.raises(dbsync.NoRemoteDB):
        dbsync.pull(tmp_path / "hkia.db")
    assert dbsync.main(["pull", "--db", str(tmp_path / "hkia.db")]) == 1


def test_pull_offline_keeps_local(tmp_path, monkeypatch):
    dest = make_db(tmp_path / "hkia.db", 3)

    def down(*a, **k):
        raise TimeoutError("no network")
    monkeypatch.setattr(dbsync, "_fetch", down)
    assert dbsync.pull(dest).startswith("offline")
    with pytest.raises(dbsync.NoRemoteDB):
        dbsync.pull(tmp_path / "missing.db")


def test_push_guards_refuse_small_or_corrupt_db(tmp_path, monkeypatch):
    small = make_db(tmp_path / "small.db", 5)
    with pytest.raises(RuntimeError, match="flights has 5 rows"):
        dbsync.validate_for_push(small)
    monkeypatch.setattr(dbsync, "MIN_FLIGHTS", 5)
    assert dbsync.validate_for_push(small)["flights"] == 5
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not a database" * 100)
    with pytest.raises((RuntimeError, sqlite3.DatabaseError)):
        dbsync.validate_for_push(corrupt)
    with pytest.raises(RuntimeError):
        dbsync.validate_for_push(tmp_path / "nope.db")


def test_push_uploads_db_then_sidecar(tmp_path, monkeypatch):
    db = make_db(tmp_path / "hkia.db", 12)
    monkeypatch.setattr(dbsync, "MIN_FLIGHTS", 10)
    calls = []

    class CP:
        returncode = 0

    def fake_gh(*args, check=True):
        calls.append(args)
        return CP()
    monkeypatch.setattr(dbsync, "_gh", fake_gh)
    msg = dbsync.push(db)
    uploads = [c for c in calls if c[:2] == ("release", "upload")]
    assert [Path(c[3]).name for c in uploads] == ["hkia.db", "hkia.db.meta.json"]
    assert "--clobber" in uploads[0]
    assert msg.startswith("uploaded") and "flights=12" in msg
    assert json.loads(dbsync.sidecar(db).read_text())["rows"]["flights"] == 12


def test_writable_dest_prefers_requested_location(tmp_path):
    want = tmp_path / "sub" / "hkia.db"
    assert dbsync.writable_dest(want) == want and want.parent.is_dir()
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o500)
    try:
        alt = dbsync.writable_dest(ro / "hkia.db")
        assert alt != ro / "hkia.db" and alt.name == "hkia.db"
    finally:
        ro.chmod(0o700)
