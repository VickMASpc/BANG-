from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gamehub_manager.core.constants import PLACEHOLDER_COVER_TEXT


class GameDetailsPanel(QWidget):
    install_requested = Signal()
    launch_requested = Signal()
    uninstall_requested = Signal()
    repair_requested = Signal()
    verify_requested = Signal()
    edit_metadata_requested = Signal()
    open_source_requested = Signal()
    open_install_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.cover_label = QLabel(PLACEHOLDER_COVER_TEXT)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setFrameShape(QFrame.Box)
        self.cover_label.setMinimumHeight(180)

        self.form = QFormLayout()
        self.title_value = QLabel("")
        self.type_value = QLabel("")
        self.genre_value = QLabel("")
        self.version_value = QLabel("")
        self.install_status_value = QLabel("")
        self.source_path_value = QLabel("")
        self.install_path_value = QLabel("")
        self.launch_target_value = QLabel("")
        self.save_path_value = QLabel("")
        self.playtime_value = QLabel("")
        self.last_played_value = QLabel("")

        self.form.addRow("Title", self.title_value)
        self.form.addRow("Game type", self.type_value)
        self.form.addRow("Genre", self.genre_value)
        self.form.addRow("Version", self.version_value)
        self.form.addRow("Install status", self.install_status_value)
        self.form.addRow("Source path", self.source_path_value)
        self.form.addRow("Local install path", self.install_path_value)
        self.form.addRow("Executable/ROM", self.launch_target_value)
        self.form.addRow("Save path", self.save_path_value)
        self.form.addRow("Playtime", self.playtime_value)
        self.form.addRow("Last played", self.last_played_value)

        actions_layout = QGridLayout()
        self._buttons: list[QPushButton] = []
        for index, label in enumerate(
            [
                "Install",
                "Launch",
                "Uninstall",
                "Repair",
                "Verify",
                "Edit Metadata",
                "Open Source Folder",
                "Open Install Folder",
            ]
        ):
            button = QPushButton(label)
            button.setEnabled(False)
            button.clicked.connect(self._emit_button_signal(index))
            actions_layout.addWidget(button, index // 2, index % 2)
            self._buttons.append(button)

        layout.addWidget(self.cover_label)
        layout.addLayout(self.form)
        layout.addLayout(actions_layout)
        layout.addStretch(1)
        self.set_game({})

    def set_game(self, game: dict[str, Any]) -> None:
        title = game.get("title") or "Select a game"
        self.cover_label.setText(game.get("cover_label") or game.get("cover_image_path") or PLACEHOLDER_COVER_TEXT)
        self.title_value.setText(title)
        self.type_value.setText(str(game.get("game_type") or ""))
        self.genre_value.setText(str(game.get("genre") or ""))
        self.version_value.setText(str(game.get("version") or ""))
        self.install_status_value.setText(str(game.get("install_status_label") or game.get("install_status") or "Not installed"))
        self.source_path_value.setText(str(game.get("source_relative_path") or ""))
        self.install_path_value.setText(str(game.get("local_path") or ""))
        launch_target = game.get("launch_target_label") or game.get("executable_path") or game.get("rom_path") or ""
        self.launch_target_value.setText(str(launch_target))
        self.save_path_value.setText(str(game.get("save_path") or ""))
        self.playtime_value.setText(self._format_playtime(game.get("total_seconds")))
        self.last_played_value.setText(str(game.get("last_played_at") or ""))
        self._update_button_states(game)

    @staticmethod
    def _format_playtime(total_seconds: Any) -> str:
        if not total_seconds:
            return ""
        total_seconds = int(total_seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    def _update_button_states(self, game: dict[str, Any]) -> None:
        installed = bool(game.get("local_path"))
        source_available = bool(game.get("source_drive_root_last_seen"))
        metadata_ready = game.get("metadata_status") == "ready"
        launchable = bool(game.get("is_launchable")) and installed
        buttons_enabled = [
            not installed and source_available,
            launchable,
            installed,
            installed and source_available,
            installed,
            metadata_ready,
            source_available,
            installed,
        ]
        for button, enabled in zip(self._buttons, buttons_enabled, strict=True):
            button.setEnabled(enabled)

    def _emit_button_signal(self, index: int):
        signals = [
            self.install_requested,
            self.launch_requested,
            self.uninstall_requested,
            self.repair_requested,
            self.verify_requested,
            self.edit_metadata_requested,
            self.open_source_requested,
            self.open_install_requested,
        ]

        def emit() -> None:
            signals[index].emit()

        return emit
