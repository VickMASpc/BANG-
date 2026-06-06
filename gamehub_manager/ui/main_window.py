from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from gamehub_manager.core.config import ConfigStore
from gamehub_manager.core.constants import APP_DISPLAY_NAME, SCAN_INTERVAL_MS
from gamehub_manager.core.paths import AppPaths
from gamehub_manager.db.repositories import GameRepository
from gamehub_manager.drives.initializer import DriveInitializer
from gamehub_manager.install.service import InstallerService
from gamehub_manager.launch.launcher import GameLauncher
from gamehub_manager.ui.dialogs import confirm_drive_initialization, prompt_for_install_root
from gamehub_manager.ui.game_details import GameDetailsPanel
from gamehub_manager.ui.game_table import GameTable
from gamehub_manager.ui.install_panel import InstallPanel
from gamehub_manager.ui.left_pane import LeftPane

if TYPE_CHECKING:
    from gamehub_manager.app import LibraryRefreshService


@dataclass(slots=True)
class WorkerResult:
    drives: list
    games: list[dict[str, Any]]


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class RefreshWorker(QRunnable):
    def __init__(self, task: Callable[[], Any]) -> None:
        super().__init__()
        self._task = task
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self._task()
        except Exception as exc:  # pragma: no cover - surfaced in UI
            self.signals.failed.emit(str(exc))
            return
        self.signals.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(
        self,
        app_paths: AppPaths,
        config_store: ConfigStore,
        game_repository: GameRepository,
        library_refresh_service: LibraryRefreshService,
        installer_service: InstallerService,
        launcher_service: GameLauncher,
        drive_initializer: DriveInitializer,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._app_paths = app_paths
        self._config_store = config_store
        self._game_repository = game_repository
        self._library_refresh_service = library_refresh_service
        self._installer_service = installer_service
        self._launcher_service = launcher_service
        self._drive_initializer = drive_initializer
        self._thread_pool = QThreadPool.globalInstance()
        self._refresh_in_progress = False
        self._install_prompted = False
        self._window_shown = False
        self._current_game: dict[str, object] | None = None
        self._active_workers: list[RefreshWorker] = []

        self.setWindowTitle(f"{APP_DISPLAY_NAME} v0.1")
        self.resize(1480, 860)

        central = QWidget()
        root_layout = QVBoxLayout(central)

        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(f"{APP_DISPLAY_NAME} v0.1")
        self.status_label = QLabel("Idle")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch(1)
        title_layout.addWidget(self.status_label)

        splitter = QSplitter()
        self.left_pane = LeftPane()
        self.game_table = GameTable()
        self.details_panel = GameDetailsPanel()
        self.install_panel = InstallPanel()

        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(self.game_table, 4)
        center_layout.addWidget(self.install_panel, 1)

        splitter.addWidget(self.left_pane)
        splitter.addWidget(center_widget)
        splitter.addWidget(self.details_panel)
        splitter.setSizes([260, 780, 360])

        root_layout.addWidget(title_bar)
        root_layout.addWidget(splitter)
        self.setCentralWidget(central)

        self.game_table.game_selected.connect(self.details_panel.set_game)
        self.game_table.game_selected.connect(self._set_current_game)
        self.left_pane.initialize_drive_requested.connect(self.initialize_drive)
        self.details_panel.install_requested.connect(self.install_selected_game)
        self.details_panel.launch_requested.connect(self.launch_selected_game)
        self.details_panel.uninstall_requested.connect(self.uninstall_selected_game)
        self.details_panel.repair_requested.connect(self.repair_selected_game)
        self.details_panel.verify_requested.connect(self.verify_selected_game)
        self.details_panel.open_install_requested.connect(self.open_install_folder)
        self.details_panel.open_source_requested.connect(self.open_source_folder)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(SCAN_INTERVAL_MS)
        self._poll_timer.timeout.connect(self.refresh_library)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._window_shown:
            return
        self._window_shown = True
        QTimer.singleShot(0, self.ensure_install_root_prompt)
        QTimer.singleShot(0, self.refresh_library)
        self._poll_timer.start()

    def ensure_install_root_prompt(self) -> None:
        if self._install_prompted:
            return
        self._install_prompted = True
        if self._config_store.get_install_root():
            return
        selected = prompt_for_install_root(self, self._app_paths.default_install_root)
        if selected:
            self._config_store.set_install_root(selected)

    def refresh_library(self) -> None:
        if self._refresh_in_progress:
            return
        self._refresh_in_progress = True
        self.status_label.setText("Refreshing library...")
        worker = RefreshWorker(self._library_refresh_service.refresh_library_snapshot)
        worker.signals.finished.connect(self._handle_refresh_complete)
        worker.signals.failed.connect(self._handle_refresh_failed)
        self._thread_pool.start(worker)

    def _handle_refresh_complete(self, snapshot) -> None:
        self._refresh_in_progress = False
        self.left_pane.set_drives(snapshot.drives)
        self.game_table.set_games(snapshot.games)
        self.install_panel.set_jobs(self._game_repository.list_install_jobs())
        self.status_label.setText(f"Loaded {len(snapshot.games)} game(s)")

    def _handle_refresh_failed(self, message: str) -> None:
        self._refresh_in_progress = False
        self.status_label.setText("Refresh failed")
        QMessageBox.warning(self, "Refresh Failed", message)

    def _set_current_game(self, game: dict[str, object]) -> None:
        self._current_game = game or None

    def _selected_game_or_warn(self) -> dict[str, object] | None:
        if not self._current_game:
            QMessageBox.information(self, "No game selected", "Select a game first.")
            return None
        return self._current_game

    def _run_background(self, task, on_success=None, title: str = "Working") -> None:
        self.status_label.setText(f"{title}...")
        worker = RefreshWorker(task)
        self._active_workers.append(worker)

        def cleanup(result=None) -> None:
            if worker in self._active_workers:
                self._active_workers.remove(worker)

        def handle_finished(result) -> None:
            cleanup(result)
            self._handle_background_complete(result, on_success)

        def handle_failed(message: str) -> None:
            cleanup()
            self._handle_background_failed(message)

        worker.signals.finished.connect(handle_finished)
        worker.signals.failed.connect(handle_failed)
        self._thread_pool.start(worker)

    def _handle_background_complete(self, result, on_success) -> None:
        if on_success is not None:
            on_success(result)
        self.status_label.setText("Ready")
        self.refresh_library()

    def _handle_background_failed(self, message: str) -> None:
        self.status_label.setText("Operation failed")
        QMessageBox.warning(self, "Operation Failed", message)
        self.refresh_library()

    def initialize_drive(self, drive_root: str) -> None:
        from pathlib import Path

        drive = self.left_pane.drive_for_root(drive_root)
        if drive is None or not drive.initializable:
            return
        if not confirm_drive_initialization(self, Path(drive_root), drive.errors):
            return
        self._run_background(
            lambda: self._drive_initializer.initialize_drive(Path(drive_root)),
            self._handle_drive_initialized,
            title="Initializing drive",
        )

    def _handle_drive_initialized(self, result) -> None:
        created_count = len(getattr(result, "created_paths", ()))
        if created_count:
            self.status_label.setText(f"Initialized drive ({created_count} path(s) created)")
        else:
            self.status_label.setText("Drive already had the required structure")

    def _resolve_source_path(self, game: dict[str, object]) -> Path | None:
        source_root = game.get("source_drive_root_last_seen")
        source_relative = game.get("source_relative_path")
        if not source_root or not source_relative:
            return None
        from pathlib import Path

        return Path(str(source_root)) / "GameHubDrive" / str(source_relative)

    def _resolve_install_root(self) -> Path | None:
        from pathlib import Path

        install_root = self._config_store.get_install_root()
        if not install_root:
            return None
        return Path(install_root)

    def install_selected_game(self) -> None:
        game = self._selected_game_or_warn()
        if not game:
            return
        source_path = self._resolve_source_path(game)
        install_root = self._resolve_install_root()
        if source_path is None or install_root is None:
            QMessageBox.warning(self, "Install", "Source drive or install root is unavailable.")
            return
        game_record = self._current_game_record(game)
        self._run_background(
            lambda: self._installer_service.install_game(game_record, source_path, install_root),
            title="Installing",
        )

    def launch_selected_game(self) -> None:
        game = self._selected_game_or_warn()
        if not game:
            return

        def task():
            game_record = self._current_game_record(game)
            installation = self._game_repository.get_installation(game_record.variant_key)
            if installation is None:
                raise RuntimeError("Game is not installed")
            return self._launcher_service.launch_installed_game(game_record, installation)

        self._run_background(task, title="Launching")

    def uninstall_selected_game(self) -> None:
        game = self._selected_game_or_warn()
        if not game:
            return
        game_record = self._current_game_record(game)
        self._run_background(lambda: self._installer_service.uninstall_game(game_record), title="Uninstalling")

    def verify_selected_game(self) -> None:
        game = self._selected_game_or_warn()
        if not game:
            return
        game_record = self._current_game_record(game)
        self._run_background(lambda: self._installer_service.verify_install(game_record), title="Verifying")

    def repair_selected_game(self) -> None:
        game = self._selected_game_or_warn()
        if not game:
            return
        source_path = self._resolve_source_path(game)
        install_root = self._resolve_install_root()
        if source_path is None or install_root is None:
            QMessageBox.warning(self, "Repair", "Source drive or install root is unavailable.")
            return
        game_record = self._current_game_record(game)
        self._run_background(
            lambda: self._installer_service.repair_install(game_record, source_path, install_root),
            title="Repairing",
        )

    def open_install_folder(self) -> None:
        game = self._selected_game_or_warn()
        if not game or not game.get("local_path"):
            return
        import os

        os.startfile(str(game["local_path"]))

    def open_source_folder(self) -> None:
        game = self._selected_game_or_warn()
        source_path = self._resolve_source_path(game) if game else None
        if source_path is None:
            return
        import os

        os.startfile(str(source_path))

    def _current_game_record(self, game: dict[str, object]):
        from gamehub_manager.core.models import GameRecord

        return GameRecord(
            id=str(game.get("id") or ""),
            variant_key=str(game.get("variant_key") or ""),
            title=str(game.get("title") or ""),
            game_type=str(game.get("game_type") or ""),
            genre=str(game.get("genre") or ""),
            version=str(game.get("version") or ""),
            source_type=str(game.get("source_type") or ""),
            source_relative_path=str(game.get("source_relative_path") or ""),
            source_drive_root_last_seen=game.get("source_drive_root_last_seen"),
            manifest_path_last_seen=game.get("manifest_path_last_seen"),
            cover_image_path=game.get("cover_image_path"),
            metadata_status=str(game.get("metadata_status") or ""),
            is_primary=bool(game.get("is_primary") or False),
            is_launchable=bool(game.get("is_launchable") or False),
            executable_path=game.get("executable_path"),
            rom_path=game.get("rom_path"),
            save_path=game.get("save_path"),
            working_directory=game.get("working_directory"),
            launch_args=str(game.get("launch_args") or ""),
            size_bytes=int(game.get("size_bytes") or 0),
            emulator_id=game.get("emulator_id"),
            emulator_name=game.get("emulator_name"),
            emulator_executable_path=game.get("emulator_executable_path"),
            emulator_working_directory=game.get("emulator_working_directory"),
            emulator_launch_args=str(game.get("emulator_launch_args") or ""),
            install_emulator_with_games=bool(game.get("install_emulator_with_games") or False),
            notes=str(game.get("notes") or ""),
        )
