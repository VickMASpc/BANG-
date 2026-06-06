from __future__ import annotations

from pathlib import Path

from gamehub_manager.core.constants import EMULATORS_RELATIVE, PC_GAMES_RELATIVE
from gamehub_manager.core.manifest import parse_game_folder
from gamehub_manager.core.models import DriveRecord, GameRecord


class LibraryScanner:
    def scan_drive(self, drive: DriveRecord) -> list[GameRecord]:
        if not drive.available:
            return []
        games: list[GameRecord] = []
        games.extend(self._scan_pc_games(drive))
        games.extend(self._scan_emulated_games(drive))
        return games

    def _scan_pc_games(self, drive: DriveRecord) -> list[GameRecord]:
        root = drive.library_root.joinpath(*PC_GAMES_RELATIVE)
        return self._scan_direct_game_folders(root, "pc", drive)

    def _scan_emulated_games(self, drive: DriveRecord) -> list[GameRecord]:
        emulator_root = drive.library_root.joinpath(*EMULATORS_RELATIVE)
        games: list[GameRecord] = []
        if not emulator_root.exists():
            return games
        for emulator_dir in sorted(path for path in emulator_root.iterdir() if path.is_dir()):
            for game_dir in sorted(path for path in emulator_dir.iterdir() if path.is_dir()):
                relative = game_dir.relative_to(drive.library_root)
                games.append(parse_game_folder(game_dir, relative, "emulated", drive.drive_root))
        return games

    def _scan_direct_game_folders(self, root: Path, expected_type: str, drive: DriveRecord) -> list[GameRecord]:
        games: list[GameRecord] = []
        if not root.exists():
            return games
        for game_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            relative = game_dir.relative_to(drive.library_root)
            games.append(parse_game_folder(game_dir, relative, expected_type, drive.drive_root))
        return games
