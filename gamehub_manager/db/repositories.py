from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from gamehub_manager.core.models import DriveRecord, GameRecord
from gamehub_manager.db.database import Database


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SettingsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get_install_root(self) -> str | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT value FROM settings WHERE key = ?", ("install_root",)).fetchone()
        return None if row is None else str(row["value"])

    def set_install_root(self, path: str) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO settings(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("install_root", path),
            )


class GameRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def reset_source_availability(self) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                UPDATE games
                SET source_drive_root_last_seen = NULL,
                    manifest_path_last_seen = NULL,
                    updated_at = ?
                WHERE source_type = 'drive'
                """,
                (utc_now_iso(),),
            )

    def upsert_scan_results(self, drive: DriveRecord, games: list[GameRecord]) -> None:
        with self._database.connect() as connection:
            for game in games:
                created_at = utc_now_iso()
                updated_at = utc_now_iso()
                connection.execute(
                    """
                    INSERT OR IGNORE INTO games (
                      id, variant_key, title, game_type, genre, version, source_type,
                      source_relative_path, source_drive_root_last_seen,
                      manifest_path_last_seen, cover_image_path, executable_path,
                      rom_path, save_path, working_directory, launch_args, size_bytes,
                      is_launchable, emulator_id, notes, is_primary,
                      metadata_status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        game.id,
                        game.variant_key,
                        game.title,
                        game.game_type,
                        game.genre,
                        game.version,
                        game.source_type,
                        game.source_relative_path,
                        str(drive.drive_root),
                        game.manifest_path_last_seen,
                        game.cover_image_path,
                        game.executable_path,
                        game.rom_path,
                        game.save_path,
                        game.working_directory,
                        game.launch_args,
                        game.size_bytes,
                        int(game.is_launchable),
                        game.emulator_id,
                        game.notes,
                        int(game.is_primary),
                        game.metadata_status,
                        created_at,
                        updated_at,
                    ),
                )
                connection.execute(
                    """
                    UPDATE games
                    SET id = ?,
                        title = ?,
                        game_type = ?,
                        genre = ?,
                        version = ?,
                        source_type = ?,
                        source_relative_path = ?,
                        source_drive_root_last_seen = ?,
                        manifest_path_last_seen = ?,
                        cover_image_path = ?,
                        executable_path = ?,
                        rom_path = ?,
                        save_path = ?,
                        working_directory = ?,
                        launch_args = ?,
                        size_bytes = ?,
                        is_launchable = ?,
                        emulator_id = ?,
                        notes = ?,
                        is_primary = ?,
                        metadata_status = ?,
                        updated_at = ?
                    WHERE variant_key = ?
                    """,
                    (
                        game.id,
                        game.title,
                        game.game_type,
                        game.genre,
                        game.version,
                        game.source_type,
                        game.source_relative_path,
                        str(drive.drive_root),
                        game.manifest_path_last_seen,
                        game.cover_image_path,
                        game.executable_path,
                        game.rom_path,
                        game.save_path,
                        game.working_directory,
                        game.launch_args,
                        game.size_bytes,
                        int(game.is_launchable),
                        game.emulator_id,
                        game.notes,
                        int(game.is_primary),
                        game.metadata_status,
                        updated_at,
                        game.variant_key,
                    ),
                )

    def list_games(self) -> list[dict[str, Any]]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                  g.id,
                  g.variant_key,
                  g.title,
                  g.game_type,
                  g.genre,
                  g.version,
                  g.source_type,
                  g.source_relative_path,
                  g.source_drive_root_last_seen,
                  g.manifest_path_last_seen,
                  g.cover_image_path,
                  g.executable_path,
                  g.rom_path,
                  g.save_path,
                  g.working_directory,
                  g.launch_args,
                  g.size_bytes,
                  g.is_launchable,
                  g.emulator_id,
                  g.notes,
                  g.metadata_status,
                  i.local_path,
                  i.install_status,
                  p.launch_count,
                  p.total_seconds,
                  p.last_played_at
                FROM games g
                LEFT JOIN installations i ON i.variant_key = g.variant_key
                LEFT JOIN playtime p ON p.variant_key = g.variant_key
                ORDER BY g.title COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]
