from __future__ import annotations

import json
from pathlib import Path

from gamehub_manager.core.constants import LIBRARY_ROOT_NAME


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def create_fake_drive(root: Path) -> Path:
    library_root = root / LIBRARY_ROOT_NAME
    (library_root / "games" / "PC Games").mkdir(parents=True, exist_ok=True)
    (library_root / "games" / "Emulators").mkdir(parents=True, exist_ok=True)
    write_json(
        library_root / "drive.json",
        {
            "schema_version": 1,
            "library_name": "GameHubDrive",
            "created_by": "tests",
            "folders": {
                "games": "games",
                "pc_games": "games/PC Games",
                "emulators": "games/Emulators",
            },
        },
    )
    return library_root
