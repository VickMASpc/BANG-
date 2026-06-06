from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget


def prompt_for_install_root(parent: QWidget, suggested_path: Path) -> str | None:
    selected = QFileDialog.getExistingDirectory(
        parent,
        "Choose Local Install Directory",
        str(suggested_path),
    )
    return selected or None


def confirm_drive_initialization(parent: QWidget, drive_root: Path, errors: tuple[str, ...]) -> bool:
    details = "\n".join(errors) if errors else "GameHubDrive will be created with the required folders."
    message = (
        f"Initialize {drive_root}?\n\n"
        "This creates GameHubDrive, drive.json, games, PC Games, Emulators, _imports, and _logs.\n"
        "Existing files on the drive will not be removed or reorganized.\n\n"
        f"Current status:\n{details}"
    )
    result = QMessageBox.question(
        parent,
        "Initialize Drive",
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes
