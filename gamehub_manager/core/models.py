from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class DriveRecord:
    drive_root: Path
    library_root: Path
    drive_label: str
    available: bool
    validation_status: str
    initializable: bool = False
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class GameRecord:
    id: str
    variant_key: str
    title: str
    game_type: str
    genre: str
    version: str
    source_type: str
    source_relative_path: str
    source_drive_root_last_seen: str | None
    manifest_path_last_seen: str | None
    cover_image_path: str | None
    metadata_status: str
    is_primary: bool = False
    is_launchable: bool = False
    executable_path: str | None = None
    rom_path: str | None = None
    save_path: str | None = None
    working_directory: str | None = None
    launch_args: str = ""
    size_bytes: int = 0
    emulator_id: str | None = None
    emulator_name: str | None = None
    emulator_executable_path: str | None = None
    emulator_working_directory: str | None = None
    emulator_launch_args: str = ""
    install_emulator_with_games: bool = False
    notes: str = ""
