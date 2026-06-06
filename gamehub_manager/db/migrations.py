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
  notes TEXT,
  is_primary INTEGER NOT NULL DEFAULT 0,
  metadata_status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS installations (
  installation_id TEXT PRIMARY KEY,
  variant_key TEXT NOT NULL,
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
