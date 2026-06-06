from __future__ import annotations

import string
import sys
from pathlib import Path
from typing import Callable, Iterable

from gamehub_manager.core.constants import DRIVE_JSON_NAME, EMULATORS_RELATIVE, LIBRARY_ROOT_NAME, PC_GAMES_RELATIVE
from gamehub_manager.core.models import DriveRecord

try:
    import psutil
except ImportError:  # pragma: no cover - exercised only in minimal environments
    psutil = None


class DriveDetector:
    def __init__(self, drive_roots_provider: Callable[[], Iterable[Path]] | None = None) -> None:
        self._drive_roots_provider = drive_roots_provider or self._default_drive_roots

    def scan_drives(self) -> list[DriveRecord]:
        drives: list[DriveRecord] = []
        for drive_root in self._drive_roots_provider():
            drive_root = Path(drive_root)
            library_root = drive_root / LIBRARY_ROOT_NAME
            if not library_root.exists():
                continue
            errors: list[str] = []
            if not (library_root / DRIVE_JSON_NAME).exists():
                errors.append("Missing drive.json")
            if not (library_root.joinpath(*PC_GAMES_RELATIVE)).exists():
                errors.append("Missing PC Games folder")
            if not (library_root.joinpath(*EMULATORS_RELATIVE)).exists():
                errors.append("Missing Emulators folder")
            validation_status = "valid" if not errors else "invalid"
            drives.append(
                DriveRecord(
                    drive_root=drive_root,
                    library_root=library_root,
                    drive_label=f"{drive_root} {LIBRARY_ROOT_NAME}",
                    available=not errors,
                    validation_status=validation_status,
                    errors=tuple(errors),
                )
            )
        drives.sort(key=lambda item: str(item.drive_root).lower())
        return drives

    @staticmethod
    def _default_drive_roots() -> list[Path]:
        if psutil is None:
            return DriveDetector._fallback_drive_roots()

        roots: list[Path] = []
        seen: set[str] = set()
        for partition in psutil.disk_partitions(all=False):
            mountpoint = Path(partition.mountpoint)
            key = str(mountpoint).lower()
            if key not in seen:
                seen.add(key)
                roots.append(mountpoint)
        return roots

    @staticmethod
    def _fallback_drive_roots() -> list[Path]:
        if sys.platform.startswith("win"):
            roots: list[Path] = []
            for letter in string.ascii_uppercase:
                candidate = Path(f"{letter}:\\")
                if candidate.exists():
                    roots.append(candidate)
            return roots
        return [path for path in Path("/").iterdir() if path.is_dir()]
