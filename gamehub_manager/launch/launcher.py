from __future__ import annotations

import subprocess
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from gamehub_manager.core.models import GameRecord
from gamehub_manager.db.repositories import GameRepository
from gamehub_manager.launch.emulator import build_emulator_command
from gamehub_manager.launch.process_tracker import ProcessTracker


@dataclass(slots=True)
class LaunchResult:
    session_id: str
    pid: int
    exit_code: int | None
    duration_seconds: int


class GameLauncher:
    def __init__(self, game_repository: GameRepository, process_tracker: ProcessTracker | None = None) -> None:
        self._game_repository = game_repository
        self._process_tracker = process_tracker or ProcessTracker()

    def launch_installed_game(self, game: GameRecord, installation: dict[str, str]) -> LaunchResult:
        local_path = Path(installation["local_path"])
        executable_path, arguments = self._resolve_launch_command(game, local_path, installation)
        if executable_path is None:
            raise FileNotFoundError("Unable to resolve launch target")
        working_directory = self._resolve_working_directory(game, local_path)
        session_id = self._game_repository.start_launch_session(
            game.variant_key,
            installation.get("installation_id"),
            "installed",
        )
        process = subprocess.Popen(
            [str(executable_path), *arguments],
            cwd=str(working_directory),
        )
        session_result = self._process_tracker.wait_for_process_tree(process.pid)
        self._game_repository.finish_launch_session(session_id, session_result.exit_code, session_result.duration_seconds)
        self._game_repository.upsert_playtime(
            game.variant_key,
            1,
            session_result.duration_seconds,
            datetime.now(timezone.utc).isoformat(),
        )
        return LaunchResult(
            session_id=session_id,
            pid=process.pid,
            exit_code=session_result.exit_code,
            duration_seconds=session_result.duration_seconds,
        )

    def _resolve_launch_command(
        self,
        game: GameRecord,
        local_path: Path,
        installation: dict[str, str],
    ) -> tuple[Path | None, list[str]]:
        if game.game_type == "pc":
            if not game.executable_path:
                return None, []
            executable = local_path / game.executable_path
            args = shlex.split(game.launch_args) if game.launch_args else []
            return executable, args
        executable, args = build_emulator_command(game, local_path)
        return executable, args

    def _resolve_working_directory(self, game: GameRecord, local_path: Path) -> Path:
        if game.game_type == "pc":
            if game.working_directory:
                return local_path / game.working_directory
            return local_path
        if game.emulator_working_directory:
            return local_path.parent / game.emulator_working_directory
        return local_path.parent
