from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class InstallPlan:
    variant_key: str
    source_path: Path
    destination_path: Path
    total_files: int
    total_bytes: int
    executable_path: str | None = None
    install_emulator_with_games: bool = False


@dataclass(slots=True)
class InstallProgress:
    copied_files: int
    total_files: int
    copied_bytes: int
    total_bytes: int
    current_file: str | None = None


@dataclass(slots=True)
class InstallResult:
    job_id: str
    installation_id: str | None
    status: str
    error_message: str | None = None
    shortcut_desktop_path: str | None = None
    shortcut_start_menu_path: str | None = None
