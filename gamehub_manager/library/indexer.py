from __future__ import annotations

from typing import Literal

from gamehub_manager.db.repositories import GameRepository
from gamehub_manager.library.duplicates import annotate_duplicate_state
from gamehub_manager.library.resolver import (
    resolve_cover_label,
    resolve_drive_status_label,
    resolve_install_status_label,
    resolve_launch_target,
)

LibraryQuery = Literal["all", "installed", "needs_setup", "source_unavailable"]


class LibraryIndexer:
    def __init__(self, game_repository: GameRepository) -> None:
        self._game_repository = game_repository

    def list_rows(self, query: LibraryQuery = "all", drive_root: str | None = None) -> list[dict]:
        rows = self._load_rows(query=query, drive_root=drive_root)
        return self._decorate_rows(rows)

    def refresh_primary_flags(self) -> None:
        self._game_repository.refresh_primary_flags()

    def _load_rows(self, query: LibraryQuery, drive_root: str | None) -> list[dict]:
        if drive_root:
            return self._game_repository.list_games_by_drive(drive_root)
        if query == "installed":
            return self._game_repository.list_installed_games()
        if query == "needs_setup":
            return self._game_repository.list_needs_setup_games()
        if query == "source_unavailable":
            return self._game_repository.list_source_unavailable_games()
        return self._game_repository.list_all_games()

    def _decorate_rows(self, rows: list[dict]) -> list[dict]:
        decorated: list[dict] = []
        for row in annotate_duplicate_state(rows):
            row["cover_label"] = resolve_cover_label(row)
            row["drive_status_label"] = resolve_drive_status_label(row)
            row["install_status_label"] = resolve_install_status_label(row)
            row["launch_target_label"] = resolve_launch_target(row)
            decorated.append(row)
        return decorated
