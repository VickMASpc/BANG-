from __future__ import annotations

import shlex
from pathlib import Path

from gamehub_manager.core.models import GameRecord


def resolve_emulator_executable(game: GameRecord, installed_game_path: Path) -> Path | None:
    if game.game_type != "emulated":
        return None
    executable = game.emulator_executable_path
    if not executable:
        return None
    if game.install_emulator_with_games:
        return installed_game_path.parent / executable
    return installed_game_path.parent / executable


def build_emulator_command(game: GameRecord, installed_game_path: Path) -> tuple[Path | None, list[str]]:
    executable = resolve_emulator_executable(game, installed_game_path)
    if executable is None:
        return None, []
    rom_path = installed_game_path / game.rom_path if game.rom_path else installed_game_path
    args_template = game.emulator_launch_args or game.launch_args or ""
    if args_template:
        arguments = shlex.split(args_template.replace("{rom_path}", str(rom_path)))
    else:
        arguments = [str(rom_path)]
    return executable, arguments
