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

from gamehub_manager.core.constants import APP_DISPLAY_NAME, SCAN_INTERVAL_MS
from gamehub_manager.core.paths import AppPaths
from gamehub_manager.db.repositories import GameRepository, SettingsRepository
from gamehub_manager.ui.dialogs import prompt_for_install_root
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
        settings_repository: SettingsRepository,
        game_repository: GameRepository,
        library_refresh_service: LibraryRefreshService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._app_paths = app_paths
        self._settings_repository = settings_repository
        self._game_repository = game_repository
        self._library_refresh_service = library_refresh_service
        self._thread_pool = QThreadPool.globalInstance()
        self._refresh_in_progress = False
        self._install_prompted = False
        self._window_shown = False

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
        if self._settings_repository.get_install_root():
            return
        selected = prompt_for_install_root(self, self._app_paths.default_install_root)
        if selected:
            self._settings_repository.set_install_root(selected)

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
        self.status_label.setText(f"Loaded {len(snapshot.games)} game(s)")

    def _handle_refresh_failed(self, message: str) -> None:
        self._refresh_in_progress = False
        self.status_label.setText("Refresh failed")
        QMessageBox.warning(self, "Refresh Failed", message)
