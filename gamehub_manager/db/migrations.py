from __future__ import annotations

import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS games (
  id TEXT NOT NULL,
  variant_key TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  game_type TEXT NOT NULL,
  genre TEXT,
  version TEXT,
  source_type TEXT NOT NULL,
  source_relative_path TEXT,
  source_drive_root_last_seen TEXT,
  manifest_path_last_seen TEXT,
  cover_image_path TEXT,
  executable_path TEXT,
  rom_path TEXT,
  save_path TEXT,
  working_directory TEXT,
  launch_args TEXT,
  size_bytes INTEGER NOT NULL DEFAULT 0,
  is_launchable INTEGER NOT NULL DEFAULT 0,
  emulator_id TEXT,
  emulator_name TEXT,
  emulator_executable_path TEXT,
  emulator_working_directory TEXT,
  emulator_launch_args TEXT,
  install_emulator_with_games INTEGER NOT NULL DEFAULT 0,
  notes TEXT,
  is_primary INTEGER NOT NULL DEFAULT 0,
  metadata_status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS installations (
  installation_id TEXT PRIMARY KEY,
  variant_key TEXT NOT NULL UNIQUE,
  local_path TEXT NOT NULL,
  executable_path TEXT,
  installed_at TEXT,
  install_status TEXT NOT NULL,
  source_file_count INTEGER,
  source_total_size INTEGER,
  dest_file_count INTEGER,
  dest_total_size INTEGER,
  shortcut_desktop_path TEXT,
  shortcut_start_menu_path TEXT,
  FOREIGN KEY (variant_key) REFERENCES games(variant_key)
);

CREATE TABLE IF NOT EXISTS install_jobs (
  job_id TEXT PRIMARY KEY,
  variant_key TEXT NOT NULL,
  source_path TEXT NOT NULL,
  destination_path TEXT NOT NULL,
  status TEXT NOT NULL,
  copied_files INTEGER NOT NULL DEFAULT 0,
  total_files INTEGER NOT NULL DEFAULT 0,
  copied_bytes INTEGER NOT NULL DEFAULT 0,
  total_bytes INTEGER NOT NULL DEFAULT 0,
  current_file TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (variant_key) REFERENCES games(variant_key)
);

CREATE TABLE IF NOT EXISTS launch_sessions (
  session_id TEXT PRIMARY KEY,
  variant_key TEXT NOT NULL,
  installation_id TEXT,
  launched_from TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  duration_seconds INTEGER DEFAULT 0,
  exit_code INTEGER,
  FOREIGN KEY (variant_key) REFERENCES games(variant_key)
);

CREATE TABLE IF NOT EXISTS playtime (
  variant_key TEXT PRIMARY KEY,
  launch_count INTEGER NOT NULL DEFAULT 0,
  total_seconds INTEGER NOT NULL DEFAULT 0,
  last_played_at TEXT
);

"""

INDEX_SQLS = (
    "CREATE INDEX IF NOT EXISTS idx_games_source_status ON games(source_drive_root_last_seen, metadata_status)",
    "CREATE INDEX IF NOT EXISTS idx_games_id ON games(id)",
    "CREATE INDEX IF NOT EXISTS idx_installations_status ON installations(install_status)",
)

TABLE_COLUMNS: dict[str, dict[str, str]] = {
    "games": {
        "id": "TEXT NOT NULL DEFAULT ''",
        "variant_key": "TEXT",
        "title": "TEXT NOT NULL DEFAULT ''",
        "game_type": "TEXT NOT NULL DEFAULT ''",
        "genre": "TEXT",
        "version": "TEXT",
        "source_type": "TEXT NOT NULL DEFAULT 'drive'",
        "source_relative_path": "TEXT",
        "source_drive_root_last_seen": "TEXT",
        "manifest_path_last_seen": "TEXT",
        "cover_image_path": "TEXT",
        "executable_path": "TEXT",
        "rom_path": "TEXT",
        "save_path": "TEXT",
        "working_directory": "TEXT",
        "launch_args": "TEXT",
        "size_bytes": "INTEGER NOT NULL DEFAULT 0",
        "is_launchable": "INTEGER NOT NULL DEFAULT 0",
        "emulator_id": "TEXT",
        "emulator_name": "TEXT",
        "emulator_executable_path": "TEXT",
        "emulator_working_directory": "TEXT",
        "emulator_launch_args": "TEXT",
        "install_emulator_with_games": "INTEGER NOT NULL DEFAULT 0",
        "notes": "TEXT",
        "is_primary": "INTEGER NOT NULL DEFAULT 0",
        "metadata_status": "TEXT NOT NULL DEFAULT 'needs_setup'",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    },
    "installations": {
        "installation_id": "TEXT",
        "variant_key": "TEXT",
        "local_path": "TEXT NOT NULL DEFAULT ''",
        "executable_path": "TEXT",
        "installed_at": "TEXT",
        "install_status": "TEXT NOT NULL DEFAULT 'installed'",
        "source_file_count": "INTEGER",
        "source_total_size": "INTEGER",
        "dest_file_count": "INTEGER",
        "dest_total_size": "INTEGER",
        "shortcut_desktop_path": "TEXT",
        "shortcut_start_menu_path": "TEXT",
    },
    "install_jobs": {
        "job_id": "TEXT",
        "variant_key": "TEXT",
        "source_path": "TEXT NOT NULL DEFAULT ''",
        "destination_path": "TEXT NOT NULL DEFAULT ''",
        "status": "TEXT NOT NULL DEFAULT 'queued'",
        "copied_files": "INTEGER NOT NULL DEFAULT 0",
        "total_files": "INTEGER NOT NULL DEFAULT 0",
        "copied_bytes": "INTEGER NOT NULL DEFAULT 0",
        "total_bytes": "INTEGER NOT NULL DEFAULT 0",
        "current_file": "TEXT",
        "error_message": "TEXT",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    },
    "launch_sessions": {
        "session_id": "TEXT",
        "variant_key": "TEXT",
        "installation_id": "TEXT",
        "launched_from": "TEXT NOT NULL DEFAULT ''",
        "started_at": "TEXT NOT NULL DEFAULT ''",
        "ended_at": "TEXT",
        "duration_seconds": "INTEGER DEFAULT 0",
        "exit_code": "INTEGER",
    },
    "playtime": {
        "variant_key": "TEXT",
        "launch_count": "INTEGER NOT NULL DEFAULT 0",
        "total_seconds": "INTEGER NOT NULL DEFAULT 0",
        "last_played_at": "TEXT",
    },
}


def run_migrations(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)
    for table_name, expected_columns in TABLE_COLUMNS.items():
        _ensure_columns(connection, table_name, expected_columns)
    for sql in INDEX_SQLS:
        connection.execute(sql)


def _ensure_columns(connection: sqlite3.Connection, table_name: str, expected_columns: dict[str, str]) -> None:
    existing = {
        str(row["name"])
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_sql in expected_columns.items():
        if column_name in existing:
            continue
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
