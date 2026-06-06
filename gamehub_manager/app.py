from __future__ import annotations

import sys
from dataclasses import dataclass

from gamehub_manager.core.config import ConfigStore
from gamehub_manager.core.paths import AppPaths
from gamehub_manager.db.database import Database
from gamehub_manager.db.repositories import GameRepository
from gamehub_manager.drives.detector import DriveDetector
from gamehub_manager.drives.initializer import DriveInitializer
from gamehub_manager.drives.scanner import LibraryScanner
from gamehub_manager.install.service import InstallerService
from gamehub_manager.library.indexer import LibraryIndexer
from gamehub_manager.launch.launcher import GameLauncher


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
        library_indexer: LibraryIndexer,
    ) -> None:
        self._drive_detector = drive_detector
        self._library_scanner = library_scanner
        self._game_repository = game_repository
        self._library_indexer = library_indexer

    def refresh_library_snapshot(self) -> LibrarySnapshot:
        drives = self._drive_detector.scan_drives()
        self._game_repository.reset_source_availability()
        for drive in drives:
            if not drive.available:
                continue
            games = self._library_scanner.scan_drive(drive)
            self._game_repository.upsert_scan_results(drive, games)
        self._library_indexer.refresh_primary_flags()
        return LibrarySnapshot(drives=drives, games=self._library_indexer.list_rows())


def run() -> int:
    from PySide6.QtWidgets import QApplication

    from gamehub_manager.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("GameHubDrive Manager")

    paths = AppPaths.from_env()
    paths.ensure_bootstrap()

    database = Database(paths.database_file)
    database.initialize()

    config_store = ConfigStore(paths.config_file)
    game_repository = GameRepository(database)
    library_refresh_service = LibraryRefreshService(
        drive_detector=DriveDetector(),
        library_scanner=LibraryScanner(),
        game_repository=game_repository,
        library_indexer=LibraryIndexer(game_repository),
    )
    installer_service = InstallerService(game_repository)
    launcher_service = GameLauncher(game_repository)
    drive_initializer = DriveInitializer()

    window = MainWindow(
        app_paths=paths,
        config_store=config_store,
        game_repository=game_repository,
        library_refresh_service=library_refresh_service,
        installer_service=installer_service,
        launcher_service=launcher_service,
        drive_initializer=drive_initializer,
    )
    window.show()
    return app.exec()
