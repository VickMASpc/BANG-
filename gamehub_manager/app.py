from __future__ import annotations

import sys
from dataclasses import dataclass

from gamehub_manager.core.paths import AppPaths
from gamehub_manager.db.database import Database
from gamehub_manager.db.repositories import GameRepository, SettingsRepository
from gamehub_manager.drives.detector import DriveDetector
from gamehub_manager.drives.scanner import LibraryScanner


@dataclass(slots=True)
class LibrarySnapshot:
    drives: list
    games: list


class LibraryRefreshService:
    def __init__(
        self,
        drive_detector: DriveDetector,
        library_scanner: LibraryScanner,
        game_repository: GameRepository,
    ) -> None:
        self._drive_detector = drive_detector
        self._library_scanner = library_scanner
        self._game_repository = game_repository

    def refresh_library_snapshot(self) -> LibrarySnapshot:
        drives = self._drive_detector.scan_drives()
        self._game_repository.reset_source_availability()
        for drive in drives:
            if not drive.available:
                continue
            games = self._library_scanner.scan_drive(drive)
            self._game_repository.upsert_scan_results(drive, games)
        return LibrarySnapshot(drives=drives, games=self._game_repository.list_games())


def run() -> int:
    from PySide6.QtWidgets import QApplication

    from gamehub_manager.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("GameHubDrive Manager")

    paths = AppPaths.from_env()
    paths.ensure_bootstrap()

    database = Database(paths.database_file)
    database.initialize()

    settings_repository = SettingsRepository(database)
    game_repository = GameRepository(database)
    library_refresh_service = LibraryRefreshService(
        drive_detector=DriveDetector(),
        library_scanner=LibraryScanner(),
        game_repository=game_repository,
    )

    window = MainWindow(
        app_paths=paths,
        settings_repository=settings_repository,
        game_repository=game_repository,
        library_refresh_service=library_refresh_service,
    )
    window.show()
    return app.exec()
