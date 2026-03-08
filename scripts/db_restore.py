#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


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
    parser = argparse.ArgumentParser(description="Restore SQLite DB from compressed backup file.")
    parser.add_argument("--db-path", type=Path, default=default_db_path(), help="Target SQLite DB path")
    parser.add_argument("--backup-file", type=Path, default=None, help="Backup .sqlite3.gz file to restore")
    parser.add_argument("--backup-dir", type=Path, default=None, help="Directory to auto-pick latest backup from")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    return parser.parse_args()


def latest_backup_file(backup_dir: Path) -> Path | None:
    files = sorted(backup_dir.glob("data-*.sqlite3.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def check_sqlite_ok(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute("PRAGMA integrity_check;").fetchone()
        result = (row[0] if row else "").lower()
        if result != "ok":
            raise RuntimeError(f"Integrity check failed: {result}")
    finally:
        conn.close()


def gunzip_to_file(source_gz: Path, target_sqlite: Path) -> None:
    with gzip.open(source_gz, "rb") as in_fh, target_sqlite.open("wb") as out_fh:
        shutil.copyfileobj(in_fh, out_fh, length=1024 * 1024)


def main() -> int:
    args = parse_args()
    db_path = args.db_path.expanduser()
    backup_dir = (args.backup_dir.expanduser() if args.backup_dir else default_backup_dir(db_path))
    backup_file = args.backup_file.expanduser() if args.backup_file else latest_backup_file(backup_dir)

    if not backup_file or not backup_file.exists():
        print("ERROR: Backup file not found.", file=sys.stderr)
        return 2

    if not args.yes:
        print(f"Restore target DB: {db_path}")
        print(f"From backup file : {backup_file}")
        answer = input("Proceed? (yes/no): ").strip().lower()
        if answer != "yes":
            print("Aborted.")
            return 1

    db_path.parent.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    temp_restore = db_path.parent / f".restore-{ts}.sqlite3"
    pre_restore_copy = backup_dir / f"pre-restore-{ts}.sqlite3"

    try:
        gunzip_to_file(backup_file, temp_restore)
        check_sqlite_ok(temp_restore)

        if db_path.exists():
            shutil.copy2(db_path, pre_restore_copy)

        os.replace(temp_restore, db_path)
        print(f"RESTORE_OK {db_path}")
        if pre_restore_copy.exists():
            print(f"PRE_RESTORE_BACKUP {pre_restore_copy}")
        return 0
    finally:
        if temp_restore.exists():
            temp_restore.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
