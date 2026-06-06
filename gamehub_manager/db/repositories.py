from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from gamehub_manager.core.models import DriveRecord, GameRecord
from gamehub_manager.db.database import Database
from gamehub_manager.library.duplicates import compute_primary_variant_keys


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
    BASE_SELECT_SQL = """
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
          g.emulator_name,
          g.emulator_executable_path,
          g.emulator_working_directory,
          g.emulator_launch_args,
          g.install_emulator_with_games,
          g.notes,
          g.is_primary,
          g.metadata_status,
          i.local_path,
          i.install_status,
          i.installation_id,
          i.executable_path AS installed_executable_path,
          i.installed_at,
          i.source_file_count,
          i.source_total_size,
          i.dest_file_count,
          i.dest_total_size,
          i.shortcut_desktop_path,
          i.shortcut_start_menu_path,
          p.launch_count,
          p.total_seconds,
          p.last_played_at
        FROM games g
        LEFT JOIN installations i ON i.variant_key = g.variant_key
        LEFT JOIN playtime p ON p.variant_key = g.variant_key
    """

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
        self.refresh_primary_flags()

    def upsert_scan_results(self, drive: DriveRecord, games: list[GameRecord]) -> None:
        with self._database.connect() as connection:
            for game in games:
                payload = self._game_payload(drive, game)
                connection.execute(
                    """
                    INSERT INTO games (
                      id, variant_key, title, game_type, genre, version, source_type,
                      source_relative_path, source_drive_root_last_seen,
                      manifest_path_last_seen, cover_image_path, executable_path,
                      rom_path, save_path, working_directory, launch_args, size_bytes,
                      is_launchable, emulator_id, emulator_name, emulator_executable_path,
                      emulator_working_directory, emulator_launch_args,
                      install_emulator_with_games, notes, is_primary,
                      metadata_status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(variant_key) DO UPDATE SET
                      id = excluded.id,
                      title = excluded.title,
                      game_type = excluded.game_type,
                      genre = excluded.genre,
                      version = excluded.version,
                      source_type = excluded.source_type,
                      source_relative_path = excluded.source_relative_path,
                      source_drive_root_last_seen = excluded.source_drive_root_last_seen,
                      manifest_path_last_seen = excluded.manifest_path_last_seen,
                      cover_image_path = excluded.cover_image_path,
                      executable_path = excluded.executable_path,
                      rom_path = excluded.rom_path,
                      save_path = excluded.save_path,
                      working_directory = excluded.working_directory,
                      launch_args = excluded.launch_args,
                      size_bytes = excluded.size_bytes,
                      is_launchable = excluded.is_launchable,
                      emulator_id = excluded.emulator_id,
                      emulator_name = excluded.emulator_name,
                      emulator_executable_path = excluded.emulator_executable_path,
                      emulator_working_directory = excluded.emulator_working_directory,
                      emulator_launch_args = excluded.emulator_launch_args,
                      install_emulator_with_games = excluded.install_emulator_with_games,
                      notes = excluded.notes,
                      metadata_status = excluded.metadata_status,
                      updated_at = excluded.updated_at
                    """,
                    payload,
                )
        self.refresh_primary_flags()

    def list_all_games(self) -> list[dict[str, Any]]:
        return self._select_games()

    def list_games(self) -> list[dict[str, Any]]:
        return self.list_all_games()

    def list_installed_games(self) -> list[dict[str, Any]]:
        return self._select_games("WHERE i.local_path IS NOT NULL")

    def list_needs_setup_games(self) -> list[dict[str, Any]]:
        return self._select_games("WHERE g.metadata_status != 'ready'")

    def list_source_unavailable_games(self) -> list[dict[str, Any]]:
        return self._select_games("WHERE g.source_drive_root_last_seen IS NULL")

    def list_games_by_drive(self, drive_root: str) -> list[dict[str, Any]]:
        return self._select_games("WHERE g.source_drive_root_last_seen = ?", (drive_root,))

    def refresh_primary_flags(self) -> None:
        rows = self._select_games(order_by="")
        primary_variant_keys = compute_primary_variant_keys(rows)
        with self._database.connect() as connection:
            connection.execute("UPDATE games SET is_primary = 0")
            if primary_variant_keys:
                connection.executemany(
                    "UPDATE games SET is_primary = 1 WHERE variant_key = ?",
                    [(variant_key,) for variant_key in primary_variant_keys],
                )

    def get_game(self, variant_key: str) -> dict[str, Any] | None:
        rows = self._select_games("WHERE g.variant_key = ?", (variant_key,))
        return rows[0] if rows else None

    def get_installation(self, variant_key: str) -> dict[str, Any] | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM installations WHERE variant_key = ?",
                (variant_key,),
            ).fetchone()
        return None if row is None else dict(row)

    def upsert_installation(
        self,
        variant_key: str,
        local_path: Path | str,
        executable_path: str | None,
        install_status: str,
        source_file_count: int | None = None,
        source_total_size: int | None = None,
        dest_file_count: int | None = None,
        dest_total_size: int | None = None,
        shortcut_desktop_path: str | None = None,
        shortcut_start_menu_path: str | None = None,
    ) -> str:
        installation_id = uuid4().hex
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO installations (
                  installation_id, variant_key, local_path, executable_path, installed_at,
                  install_status, source_file_count, source_total_size, dest_file_count,
                  dest_total_size, shortcut_desktop_path, shortcut_start_menu_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(variant_key) DO UPDATE SET
                  local_path = excluded.local_path,
                  executable_path = excluded.executable_path,
                  installed_at = excluded.installed_at,
                  install_status = excluded.install_status,
                  source_file_count = excluded.source_file_count,
                  source_total_size = excluded.source_total_size,
                  dest_file_count = excluded.dest_file_count,
                  dest_total_size = excluded.dest_total_size,
                  shortcut_desktop_path = excluded.shortcut_desktop_path,
                  shortcut_start_menu_path = excluded.shortcut_start_menu_path
                """,
                (
                    installation_id,
                    variant_key,
                    str(local_path),
                    executable_path,
                    utc_now_iso(),
                    install_status,
                    source_file_count,
                    source_total_size,
                    dest_file_count,
                    dest_total_size,
                    shortcut_desktop_path,
                    shortcut_start_menu_path,
                ),
            )
        self.refresh_primary_flags()
        return installation_id

    def remove_installation(self, variant_key: str) -> None:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM installations WHERE variant_key = ?", (variant_key,))
        self.refresh_primary_flags()

    def upsert_install_job(
        self,
        variant_key: str,
        source_path: Path | str,
        destination_path: Path | str,
        status: str,
        total_files: int = 0,
        total_bytes: int = 0,
        copied_files: int = 0,
        copied_bytes: int = 0,
        current_file: str | None = None,
        error_message: str | None = None,
        job_id: str | None = None,
    ) -> str:
        job_id = job_id or uuid4().hex
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO install_jobs (
                  job_id, variant_key, source_path, destination_path, status,
                  copied_files, total_files, copied_bytes, total_bytes, current_file,
                  error_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                  status = excluded.status,
                  copied_files = excluded.copied_files,
                  total_files = excluded.total_files,
                  copied_bytes = excluded.copied_bytes,
                  total_bytes = excluded.total_bytes,
                  current_file = excluded.current_file,
                  error_message = excluded.error_message,
                  updated_at = excluded.updated_at
                """,
                (
                    job_id,
                    variant_key,
                    str(source_path),
                    str(destination_path),
                    status,
                    copied_files,
                    total_files,
                    copied_bytes,
                    total_bytes,
                    current_file,
                    error_message,
                    utc_now_iso(),
                    utc_now_iso(),
                ),
            )
        return job_id

    def update_install_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        copied_files: int | None = None,
        total_files: int | None = None,
        copied_bytes: int | None = None,
        total_bytes: int | None = None,
        current_file: str | None = None,
        error_message: str | None = None,
    ) -> None:
        fields: list[str] = []
        values: list[Any] = []
        for column, value in (
            ("status", status),
            ("copied_files", copied_files),
            ("total_files", total_files),
            ("copied_bytes", copied_bytes),
            ("total_bytes", total_bytes),
            ("current_file", current_file),
            ("error_message", error_message),
        ):
            if value is not None:
                fields.append(f"{column} = ?")
                values.append(value)
        if not fields:
            return
        fields.append("updated_at = ?")
        values.append(utc_now_iso())
        values.append(job_id)
        with self._database.connect() as connection:
            connection.execute(f"UPDATE install_jobs SET {', '.join(fields)} WHERE job_id = ?", values)

    def get_install_job(self, job_id: str) -> dict[str, Any] | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM install_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return None if row is None else dict(row)

    def list_install_jobs(self) -> list[dict[str, Any]]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM install_jobs ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def start_launch_session(self, variant_key: str, installation_id: str | None, launched_from: str) -> str:
        session_id = uuid4().hex
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO launch_sessions (
                  session_id, variant_key, installation_id, launched_from, started_at, duration_seconds
                ) VALUES (?, ?, ?, ?, ?, 0)
                """,
                (session_id, variant_key, installation_id, launched_from, utc_now_iso()),
            )
        return session_id

    def finish_launch_session(self, session_id: str, exit_code: int | None, duration_seconds: int) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                UPDATE launch_sessions
                SET ended_at = ?, exit_code = ?, duration_seconds = ?
                WHERE session_id = ?
                """,
                (utc_now_iso(), exit_code, duration_seconds, session_id),
            )

    def upsert_playtime(self, variant_key: str, launch_count_delta: int, total_seconds_delta: int, last_played_at: str | None) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO playtime (variant_key, launch_count, total_seconds, last_played_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(variant_key) DO UPDATE SET
                  launch_count = launch_count + excluded.launch_count,
                  total_seconds = total_seconds + excluded.total_seconds,
                  last_played_at = excluded.last_played_at
                """,
                (variant_key, launch_count_delta, total_seconds_delta, last_played_at),
            )

    def get_playtime(self, variant_key: str) -> dict[str, Any] | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM playtime WHERE variant_key = ?",
                (variant_key,),
            ).fetchone()
        return None if row is None else dict(row)

    def _select_games(
        self,
        where_clause: str = "",
        params: tuple[Any, ...] = (),
        *,
        order_by: str = "ORDER BY g.title COLLATE NOCASE, g.variant_key COLLATE NOCASE",
    ) -> list[dict[str, Any]]:
        sql = self.BASE_SELECT_SQL
        if where_clause:
            sql = f"{sql}\n{where_clause}"
        if order_by:
            sql = f"{sql}\n{order_by}"
        with self._database.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def _game_payload(self, drive: DriveRecord, game: GameRecord) -> tuple[Any, ...]:
        now = utc_now_iso()
        return (
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
            game.emulator_name,
            game.emulator_executable_path,
            game.emulator_working_directory,
            game.emulator_launch_args,
            int(game.install_emulator_with_games),
            game.notes,
            int(game.is_primary),
            game.metadata_status,
            now,
            now,
        )
