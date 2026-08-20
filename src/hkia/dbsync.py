"""Keep data/hkia.db out of git: the live SQLite file lives as a GitHub Release asset instead.

    python -m hkia.dbsync pull            # download the latest hkia.db (skips when the local copy is already current)
    python -m hkia.dbsync push            # upload data/hkia.db (+ sidecar meta) to the `data` release with `gh`
    python -m hkia.dbsync meta            # print the remote sidecar

Why a release asset: free, public URL, 2 GB/file limit (vs GitHub's 100 MB hard limit on files in git), uploadable with the
workflow's own GITHUB_TOKEN. The `concurrency: ingest` group in the workflows makes the asset single-writer — ingest and
backfill never run at the same time — so pull → mutate → push needs no locking. If a push fails the next run simply pulls the
previous copy and re-ingests; every ingest job is idempotent over a rolling window, so nothing is lost for good.

Safety rails in `push`: `PRAGMA quick_check` must pass and the `flights` table must hold at least MIN_FLIGHTS rows, so an
empty or corrupt file can never clobber the good copy. `pull` refuses to continue silently with no database at all.

Layout on the release (tag `data`, kept off "Latest"):
    hkia.db             the database
    hkia.db.meta.json   {"sha256", "size", "rows": {...}, "uploaded_at", "git_sha"} — small, fetched first so readers
                        (Streamlit every 10 min) can skip the 40+ MB download when nothing changed.
A local sidecar `<db>.meta.json` records what was last pulled/pushed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from . import db as _db

REPO = os.environ.get("HKIA_DB_REPO", "dsjwong/hkia-delay-predictor")
TAG = os.environ.get("HKIA_DB_TAG", "data")
ASSET = "hkia.db"
META_ASSET = ASSET + ".meta.json"
BASE_URL = os.environ.get("HKIA_DB_URL", f"https://github.com/{REPO}/releases/download/{TAG}/")
MIN_FLIGHTS = 10_000          # the real db has 40k+; anything below this is not the live database
ROW_TABLES = ("flights", "arrivals", "predictions", "explanations", "aircraft_links", "metar_hist", "adsb_snapshots")
TIMEOUT = 60


class NoRemoteDB(RuntimeError):
    """Neither a remote asset nor a usable local copy exists."""


# ----------------------------------------------------------------------------- helpers
def sidecar(db_path: Path) -> Path:
    return db_path.with_name(db_path.name + ".meta.json")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def row_counts(db_path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as c:
        have = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for t in ROW_TABLES:
            if t in have:
                out[t] = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    return out


def quick_check(db_path: Path) -> str:
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as c:
        return c.execute("PRAGMA quick_check").fetchone()[0]


def _git_sha() -> str | None:
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha[:7]
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True,
                              cwd=Path(__file__).parent).stdout.strip() or None
    except Exception:
        return None


def build_meta(db_path: Path) -> dict:
    return {
        "sha256": sha256_of(db_path),
        "size": db_path.stat().st_size,
        "rows": row_counts(db_path),
        "uploaded_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "git_sha": _git_sha(),
    }


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _fetch(url: str, dest: Path | None = None, timeout: int = TIMEOUT) -> bytes | None:
    """GET url; returns the body (or writes it to dest and returns b''). None on 404."""
    req = urllib.request.Request(url, headers={"User-Agent": "hkia-dbsync", "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if dest is None:
                return r.read()
            with open(dest, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            return b""
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def remote_meta() -> dict | None:
    body = _fetch(BASE_URL + META_ASSET, timeout=30)
    return json.loads(body) if body else None


def writable_dest(preferred: Path) -> Path:
    """`preferred` if its directory is (or can be made) writable, else a per-user temp location.

    Streamlit Community Cloud and most containers allow writes next to the checkout; this is the fallback for the ones
    that do not. Readers call this once and use the result as DB_PATH.
    """
    try:
        preferred.parent.mkdir(parents=True, exist_ok=True)
        probe = preferred.parent / ".write-probe"
        probe.touch()
        probe.unlink()
        return preferred
    except OSError:
        alt = Path(tempfile.gettempdir()) / "hkia" / preferred.name
        alt.parent.mkdir(parents=True, exist_ok=True)
        return alt


# ----------------------------------------------------------------------------- pull
def pull(db_path: Path | None = None, force: bool = False) -> str:
    """Make `db_path` the latest remote copy. Returns a one-line status. Never leaves a half-written file behind.

    - remote sidecar sha == local sidecar sha and the file exists → "current" (no download)
    - otherwise download to <db>.part, verify sha256 against the remote sidecar, atomically replace
    - network error / remote missing, but a local copy exists → keep it ("offline: ...")
    - nothing remote and nothing local → NoRemoteDB (callers in CI must fail loudly, never ingest into a blank db)
    """
    db_path = Path(db_path or _db.DB_PATH)
    local = _read_json(sidecar(db_path)) if db_path.exists() else None
    try:
        remote = remote_meta()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        if db_path.exists():
            return f"offline: using local copy ({e})"
        raise NoRemoteDB(f"cannot reach {BASE_URL}{META_ASSET} and no local db at {db_path}: {e}") from e

    if remote is None:
        # no sidecar: maybe the asset is there without one (hand-uploaded) — try it; else fall back / fail
        if db_path.exists() and not force:
            return "remote sidecar missing: keeping local copy"
    elif local and local.get("sha256") == remote["sha256"] and db_path.exists() and not force:
        return f"current ({remote['size'] / 1e6:.1f} MB, uploaded {remote['uploaded_at']})"

    part = db_path.with_name(db_path.name + ".part")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        got = _fetch(BASE_URL + ASSET, dest=part)
        if got is None:
            part.unlink(missing_ok=True)
            if db_path.exists():
                return "remote db missing: keeping local copy"
            raise NoRemoteDB(f"no {ASSET} on release '{TAG}' of {REPO} and no local db at {db_path}")
        if remote is not None:
            got_sha = sha256_of(part)
            if got_sha != remote["sha256"]:
                # a push may be mid-flight (clobber = delete + re-upload); do not install a torn file
                part.unlink(missing_ok=True)
                if db_path.exists():
                    return "remote checksum mismatch (upload in progress?): keeping local copy"
                raise NoRemoteDB("downloaded db does not match the remote sidecar and there is no local copy")
        if quick_check(part) != "ok":
            part.unlink(missing_ok=True)
            if db_path.exists():
                return "remote db failed quick_check: keeping local copy"
            raise NoRemoteDB("downloaded db failed PRAGMA quick_check")
        os.replace(part, db_path)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        part.unlink(missing_ok=True)
        if db_path.exists():
            return f"offline: using local copy ({e})"
        raise NoRemoteDB(f"download failed and no local db at {db_path}: {e}") from e

    meta = remote or build_meta(db_path)
    sidecar(db_path).write_text(json.dumps(meta, indent=1))
    return f"downloaded {db_path.stat().st_size / 1e6:.1f} MB (uploaded {meta.get('uploaded_at')}, sha {meta['sha256'][:8]})"


# ----------------------------------------------------------------------------- push
def _gh(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=check)


def ensure_release() -> None:
    if _gh("release", "view", TAG, "--repo", REPO, check=False).returncode == 0:
        return
    _gh("release", "create", TAG, "--repo", REPO, "--title", "Live database (auto-updated)", "--latest=false",
        "--notes", "Rolling SQLite database written by the ingest/backfill workflows every 30 min. "
                   "Not a software release: download `hkia.db` (or run `python -m hkia.dbsync pull`). "
                   "`hkia.db.meta.json` carries the sha256 / row counts / upload time.")


def validate_for_push(db_path: Path) -> dict:
    """Raise if this file must not replace the remote copy. Returns the row counts."""
    if not db_path.exists():
        raise RuntimeError(f"{db_path} does not exist")
    qc = quick_check(db_path)
    if qc != "ok":
        raise RuntimeError(f"refusing to push: PRAGMA quick_check = {qc!r}")
    rows = row_counts(db_path)
    if rows.get("flights", 0) < MIN_FLIGHTS:
        raise RuntimeError(f"refusing to push: flights has {rows.get('flights', 0)} rows (< {MIN_FLIGHTS}); "
                           "this is not the live database")
    return rows


def push(db_path: Path | None = None, retries: int = 3) -> str:
    db_path = Path(db_path or _db.DB_PATH)
    validate_for_push(db_path)
    # fold any WAL into the main file so the uploaded bytes are self-contained
    with sqlite3.connect(db_path) as c:
        c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    meta = build_meta(db_path)
    ensure_release()
    with tempfile.TemporaryDirectory() as td:
        meta_path = Path(td) / META_ASSET
        meta_path.write_text(json.dumps(meta, indent=1))
        last: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                # db first, sidecar last: a reader that sees the new sidecar can expect the new db to be there
                _gh("release", "upload", TAG, str(db_path), "--repo", REPO, "--clobber")
                _gh("release", "upload", TAG, str(meta_path), "--repo", REPO, "--clobber")
                last = None
                break
            except subprocess.CalledProcessError as e:
                last = RuntimeError(f"gh release upload failed (attempt {attempt}/{retries}): {e.stderr.strip()}")
                print(last, file=sys.stderr)
        if last:
            raise last
    sidecar(db_path).write_text(json.dumps(meta, indent=1))
    rows = ", ".join(f"{k}={v:,}" for k, v in meta["rows"].items())
    return f"uploaded {meta['size'] / 1e6:.1f} MB to {REPO}@{TAG} (sha {meta['sha256'][:8]}; {rows})"


# ----------------------------------------------------------------------------- cli
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["pull", "push", "meta"])
    ap.add_argument("--db", type=Path, default=None, help=f"database path (default {_db.DB_PATH})")
    ap.add_argument("--force", action="store_true", help="pull: re-download even if the local copy is current")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "pull":
            print(pull(a.db, force=a.force))
        elif a.cmd == "push":
            print(push(a.db))
        else:
            print(json.dumps(remote_meta(), indent=1))
    except (NoRemoteDB, RuntimeError) as e:
        print(f"dbsync {a.cmd}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
