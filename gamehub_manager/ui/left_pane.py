from __future__ import annotations

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gamehub_manager.core.models import DriveRecord


class LeftPane(QWidget):
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
        drives_layout.addWidget(self.drives_list)
        drives_layout.addWidget(self.drive_summary)

        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(QLabel("Prototype slice"))
        footer_layout.addStretch(1)

        layout.addWidget(library_group)
        layout.addWidget(drives_group)
        layout.addWidget(footer)

    def set_drives(self, drives: list[DriveRecord]) -> None:
        self.drives_list.clear()
        if not drives:
            self.drive_summary.setText("No compatible drives detected.")
            return
        valid_count = 0
        for drive in drives:
            label = drive.drive_label
            if drive.validation_status != "valid":
                label = f"{label} ({drive.validation_status})"
            QListWidgetItem(label, self.drives_list)
            if drive.available:
                valid_count += 1
        self.drive_summary.setText(f"{valid_count} valid drive(s), {len(drives) - valid_count} invalid.")
