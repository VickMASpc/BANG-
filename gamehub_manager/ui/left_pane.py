from __future__ import annotations

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Signal, Qt

from gamehub_manager.core.models import DriveRecord


class LeftPane(QWidget):
    initialize_drive_requested = Signal(str)

    STATIC_ITEMS = [
        "All Games",
        "Installed Library",
        "Disconnected Sources",
        "Needs Setup",
        "Install Queue",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        library_group = QGroupBox("Library")
        library_layout = QVBoxLayout(library_group)
        self.library_list = QListWidget()
        for item in self.STATIC_ITEMS:
            QListWidgetItem(item, self.library_list)
        library_layout.addWidget(self.library_list)

        drives_group = QGroupBox("Detected Drives")
        drives_layout = QVBoxLayout(drives_group)
        self.drives_list = QListWidget()
        self.drive_summary = QLabel("No compatible drives detected.")
        self.initialize_button = QPushButton("Initialize Selected Drive")
        self.initialize_button.setEnabled(False)
        self.initialize_button.clicked.connect(self._emit_initialize_requested)
        drives_layout.addWidget(self.drives_list)
        drives_layout.addWidget(self.drive_summary)
        drives_layout.addWidget(self.initialize_button)
        self.drives_list.currentRowChanged.connect(self._update_initialize_button_state)

        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(QLabel("Prototype slice"))
        footer_layout.addStretch(1)

        layout.addWidget(library_group)
        layout.addWidget(drives_group)
        layout.addWidget(footer)
        self._drives: list[DriveRecord] = []

    def set_drives(self, drives: list[DriveRecord]) -> None:
        self._drives = drives
        self.drives_list.clear()
        if not drives:
            self.drive_summary.setText("No compatible drives detected.")
            self.initialize_button.setEnabled(False)
            return
        valid_count = 0
        for drive in drives:
            label = drive.drive_label
            if drive.validation_status == "valid":
                label = f"{label} - Compatible"
            elif drive.initializable:
                label = f"{label} - Needs initialization"
            else:
                label = f"{label} - Invalid"
            item = QListWidgetItem(label, self.drives_list)
            item.setData(Qt.UserRole, str(drive.drive_root))
            if drive.errors:
                item.setToolTip("\n".join(drive.errors))
            if drive.available:
                valid_count += 1
        candidate_count = sum(1 for drive in drives if drive.initializable and not drive.available)
        invalid_count = sum(1 for drive in drives if not drive.available and not drive.initializable)
        self.drive_summary.setText(
            f"{valid_count} compatible, {candidate_count} initializable, {invalid_count} invalid."
        )
        self._update_initialize_button_state()

    def _update_initialize_button_state(self, *_args) -> None:
        current_row = self.drives_list.currentRow()
        if current_row < 0 or current_row >= len(self._drives):
            self.initialize_button.setEnabled(False)
            return
        self.initialize_button.setEnabled(self._drives[current_row].initializable)

    def _emit_initialize_requested(self) -> None:
        current_row = self.drives_list.currentRow()
        if current_row < 0 or current_row >= len(self._drives):
            return
        drive = self._drives[current_row]
        if not drive.initializable:
            return
        self.initialize_drive_requested.emit(str(drive.drive_root))

    def drive_for_root(self, drive_root: str) -> DriveRecord | None:
        return next((drive for drive in self._drives if str(drive.drive_root) == drive_root), None)
