#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


def default_db_path() -> Path:
    env_path = os.getenv("DATABASE_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    if Path("/var/data").exists():
        return Path("/var/data/data.db")
    return Path(__file__).resolve().parents[1] / "data.db"


def default_backup_dir(db_path: Path) -> Path:
    env_path = os.getenv("BACKUP_DIR", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    if db_path.parent == Path("/var/data"):
        return Path("/var/data/backups")
    return db_path.parent / "backups"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create compressed SQLite backup with retention pruning.")
    parser.add_argument("--db-path", type=Path, default=default_db_path(), help="SQLite DB path")
    parser.add_argument("--backup-dir", type=Path, default=None, help="Backup directory")
    parser.add_argument("--retain-days", type=int, default=14, help="Delete backups older than this")
    parser.add_argument("--keep-min", type=int, default=14, help="Always keep at least this many latest backups")
    parser.add_argument("--prefix", type=str, default="data", help="Backup file prefix")
    parser.add_argument("--no-prune", action="store_true", help="Skip retention pruning")
    return parser.parse_args()


def ensure_integrity(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("PRAGMA integrity_check;").fetchone()
        result = (row[0] if row else "").lower()
        if result != "ok":
            raise RuntimeError(f"Source DB integrity check failed: {result}")
    finally:
        conn.close()


def safe_backup(source: Path, target: Path) -> None:
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def gzip_file(source: Path, target: Path) -> None:
    with source.open("rb") as in_fh, gzip.open(target, "wb", compresslevel=9) as out_fh:
        while True:
            chunk = in_fh.read(1024 * 1024)
            if not chunk:
                break
            out_fh.write(chunk)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def iter_backup_files(backup_dir: Path, prefix: str) -> Iterable[Path]:
    return sorted(backup_dir.glob(f"{prefix}-*.sqlite3.gz"), key=lambda p: p.stat().st_mtime, reverse=True)


def prune_old_backups(backup_dir: Path, prefix: str, retain_days: int, keep_min: int) -> int:
    files = list(iter_backup_files(backup_dir, prefix))
    if not files:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(retain_days, 0))
    deleted = 0
    for idx, path in enumerate(files):
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if idx < keep_min:
            continue
        if mtime < cutoff:
            path.unlink(missing_ok=True)
            sha_path = path.with_suffix(path.suffix + ".sha256")
            sha_path.unlink(missing_ok=True)
            meta_path = path.with_suffix(path.suffix + ".json")
            meta_path.unlink(missing_ok=True)
            deleted += 1
    return deleted


def main() -> int:
    args = parse_args()
    db_path = args.db_path.expanduser()
    backup_dir = (args.backup_dir.expanduser() if args.backup_dir else default_backup_dir(db_path))
    backup_dir.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        print(f"ERROR: DB not found: {db_path}", file=sys.stderr)
        return 2

    ensure_integrity(db_path)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    raw_path = backup_dir / f"{args.prefix}-{stamp}.sqlite3"
    gz_path = backup_dir / f"{args.prefix}-{stamp}.sqlite3.gz"

    safe_backup(db_path, raw_path)
    gzip_file(raw_path, gz_path)
    raw_path.unlink(missing_ok=True)

    checksum = file_sha256(gz_path)
    sha_path = gz_path.with_suffix(gz_path.suffix + ".sha256")
    sha_path.write_text(f"{checksum}  {gz_path.name}\n", encoding="utf-8")

    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_db": str(db_path),
        "backup_file": gz_path.name,
        "sha256": checksum,
        "size_bytes": gz_path.stat().st_size,
        "retain_days": args.retain_days,
        "keep_min": args.keep_min,
    }
    meta_path = gz_path.with_suffix(gz_path.suffix + ".json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")

    deleted = 0
    if not args.no_prune:
        deleted = prune_old_backups(backup_dir, args.prefix, args.retain_days, args.keep_min)

    print(f"BACKUP_OK {gz_path}")
    print(f"SHA256 {checksum}")
    print(f"PRUNED {deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
