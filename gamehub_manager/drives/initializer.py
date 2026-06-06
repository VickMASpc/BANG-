from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from gamehub_manager.core.constants import DRIVE_JSON_NAME, LIBRARY_ROOT_NAME

REQUIRED_DIRECTORIES: tuple[tuple[str, ...], ...] = (
    (),
    ("games",),
    ("games", "PC Games"),
    ("games", "Emulators"),
    ("_imports",),
    ("_logs",),
)

DRIVE_JSON_PAYLOAD = {
    "schema_version": 1,
    "library_name": LIBRARY_ROOT_NAME,
    "created_by": "GameHubDrive Manager",
    "notes": "",
    "folders": {
        "games": "games",
        "pc_games": "games/PC Games",
        "emulators": "games/Emulators",
    },
}


@dataclass(slots=True)
class DriveInitializationResult:
    drive_root: Path
    library_root: Path
    created_paths: tuple[Path, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)


class DriveInitializer:
    def initialize_drive(self, drive_root: Path) -> DriveInitializationResult:
        drive_root = Path(drive_root)
        if not drive_root.exists() or not drive_root.is_dir():
            raise FileNotFoundError(f"Drive root is unavailable: {drive_root}")

        library_root = drive_root / LIBRARY_ROOT_NAME
        created_paths: list[Path] = []
        warnings: list[str] = []

        for relative_parts in REQUIRED_DIRECTORIES:
            target = library_root.joinpath(*relative_parts)
            if target.exists():
                if not target.is_dir():
                    raise RuntimeError(f"Cannot initialize drive because {target} is not a directory.")
                continue
            target.mkdir(parents=True, exist_ok=False)
            created_paths.append(target)

        drive_json_path = library_root / DRIVE_JSON_NAME
        if drive_json_path.exists():
            if not drive_json_path.is_file():
                raise RuntimeError(f"Cannot initialize drive because {drive_json_path} is not a file.")
            warnings.append("drive.json already exists and was left unchanged.")
        else:
            drive_json_path.write_text(
                json.dumps(DRIVE_JSON_PAYLOAD, indent=2) + "\n",
                encoding="utf-8",
            )
            created_paths.append(drive_json_path)

        return DriveInitializationResult(
            drive_root=drive_root,
            library_root=library_root,
            created_paths=tuple(created_paths),
            warnings=tuple(warnings),
        )
