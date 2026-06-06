from __future__ import annotations

import ctypes
import json
import string
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from gamehub_manager.core.constants import DRIVE_JSON_NAME, LIBRARY_ROOT_NAME
from gamehub_manager.core.models import DriveRecord
from gamehub_manager.drives.initializer import DRIVE_JSON_PAYLOAD, REQUIRED_DIRECTORIES

try:
    import psutil
except ImportError:  # pragma: no cover - exercised only in minimal environments
    psutil = None


@dataclass(slots=True)
class DriveValidationResult:
    status: str
    errors: tuple[str, ...]
    initializable: bool


class WindowsVolumeEnumerator:
    DRIVE_REMOVABLE = 2
    DRIVE_FIXED = 3
    CANDIDATE_TYPES = {DRIVE_REMOVABLE, DRIVE_FIXED}

    @classmethod
    def list_roots(cls) -> list[Path]:
        kernel32 = getattr(ctypes, "windll", None)
        if kernel32 is None:
            return cls._fallback_roots()

        mask = kernel32.kernel32.GetLogicalDrives()
        if mask == 0:
            return cls._fallback_roots()

        roots: list[Path] = []
        for index, letter in enumerate(string.ascii_uppercase):
            if not mask & (1 << index):
                continue
            root = Path(f"{letter}:\\")
            drive_type = kernel32.kernel32.GetDriveTypeW(str(root))
            if drive_type in cls.CANDIDATE_TYPES:
                roots.append(root)
        return roots

    @staticmethod
    def _fallback_roots() -> list[Path]:
        roots: list[Path] = []
        for letter in string.ascii_uppercase:
            candidate = Path(f"{letter}:\\")
            if candidate.exists():
                roots.append(candidate)
        return roots


class DriveDetector:
    def __init__(self, drive_roots_provider: Callable[[], Iterable[Path]] | None = None) -> None:
        self._drive_roots_provider = drive_roots_provider or self._default_drive_roots

    def scan_drives(self) -> list[DriveRecord]:
        drives: list[DriveRecord] = []
        seen: set[str] = set()

        for drive_root in self._drive_roots_provider():
            drive_root = Path(drive_root)
            key = str(drive_root).lower()
            if key in seen:
                continue
            seen.add(key)

            library_root = drive_root / LIBRARY_ROOT_NAME
            validation = self._validate_drive(drive_root, library_root)
            drives.append(
                DriveRecord(
                    drive_root=drive_root,
                    library_root=library_root,
                    drive_label=str(drive_root),
                    available=validation.status == "valid",
                    validation_status=validation.status,
                    initializable=validation.initializable,
                    errors=validation.errors,
                )
            )

        drives.sort(key=lambda item: str(item.drive_root).lower())
        return drives

    def _validate_drive(self, drive_root: Path, library_root: Path) -> DriveValidationResult:
        if not drive_root.exists() or not drive_root.is_dir():
            return DriveValidationResult(
                status="invalid",
                errors=(f"Drive root is unavailable: {drive_root}",),
                initializable=False,
            )
        if not library_root.exists():
            return DriveValidationResult(
                status="missing",
                errors=(f"Missing {LIBRARY_ROOT_NAME} folder",),
                initializable=True,
            )

        errors: list[str] = []
        initializable = True

        if not library_root.is_dir():
            return DriveValidationResult(
                status="invalid",
                errors=(f"{LIBRARY_ROOT_NAME} exists but is not a directory",),
                initializable=False,
            )

        for relative_parts in REQUIRED_DIRECTORIES[1:]:
            target = library_root.joinpath(*relative_parts)
            relative_path = Path(*relative_parts).as_posix()
            if not target.exists():
                errors.append(f"Missing folder: {relative_path}")
                continue
            if not target.is_dir():
                errors.append(f"Expected folder but found file: {relative_path}")
                initializable = False

        drive_json_path = library_root / DRIVE_JSON_NAME
        if not drive_json_path.exists():
            errors.append(f"Missing {DRIVE_JSON_NAME}")
        elif not drive_json_path.is_file():
            errors.append(f"{DRIVE_JSON_NAME} exists but is not a file")
            initializable = False
        else:
            drive_json_errors = self._validate_drive_json(drive_json_path)
            errors.extend(drive_json_errors)
            if drive_json_errors:
                initializable = False

        return DriveValidationResult(
            status="valid" if not errors else "invalid",
            errors=tuple(errors),
            initializable=initializable,
        )

    def _validate_drive_json(self, drive_json_path: Path) -> list[str]:
        try:
            payload = json.loads(drive_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return [f"Malformed {DRIVE_JSON_NAME}: {exc.msg}"]
        except OSError as exc:
            return [f"Unable to read {DRIVE_JSON_NAME}: {exc}"]

        if not isinstance(payload, dict):
            return [f"Malformed {DRIVE_JSON_NAME}: root value must be an object"]

        errors: list[str] = []
        self._validate_field(payload, "schema_version", DRIVE_JSON_PAYLOAD["schema_version"], errors)
        self._validate_field(payload, "library_name", DRIVE_JSON_PAYLOAD["library_name"], errors)
        self._validate_field(payload, "created_by", DRIVE_JSON_PAYLOAD["created_by"], errors)

        notes = payload.get("notes")
        if not isinstance(notes, str):
            errors.append("Invalid drive.json field: notes must be a string")

        folders = payload.get("folders")
        if not isinstance(folders, dict):
            errors.append("Invalid drive.json field: folders must be an object")
            return errors

        expected_folders = DRIVE_JSON_PAYLOAD["folders"]
        for key, expected_value in expected_folders.items():
            actual_value = folders.get(key)
            if actual_value != expected_value:
                errors.append(f"Invalid drive.json folders.{key}: expected {expected_value!r}")

        return errors

    @staticmethod
    def _validate_field(payload: dict[str, Any], field_name: str, expected_value: Any, errors: list[str]) -> None:
        if payload.get(field_name) != expected_value:
            errors.append(f"Invalid drive.json field: {field_name} must be {expected_value!r}")

    @staticmethod
    def _default_drive_roots() -> list[Path]:
        if sys.platform.startswith("win"):
            return WindowsVolumeEnumerator.list_roots()
        if psutil is not None:
            roots: list[Path] = []
            seen: set[str] = set()
            for partition in psutil.disk_partitions(all=False):
                mountpoint = Path(partition.mountpoint)
                key = str(mountpoint).lower()
                if key not in seen:
                    seen.add(key)
                    roots.append(mountpoint)
            return roots
        return [path for path in Path("/").iterdir() if path.is_dir()]
