from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget


def prompt_for_install_root(parent: QWidget, suggested_path: Path) -> str | None:
    selected = QFileDialog.getExistingDirectory(
        parent,
        "Choose Local Install Directory",
        str(suggested_path),
    )
    return selected or None
