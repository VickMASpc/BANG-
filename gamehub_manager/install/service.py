from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from gamehub_manager.core.models import GameRecord
from gamehub_manager.db.repositories import GameRepository
from gamehub_manager.install.copier import InstallCopier
from gamehub_manager.install.jobs import InstallResult
from gamehub_manager.install.planner import InstallPlanner
from gamehub_manager.install.shortcuts import ShortcutService
from gamehub_manager.install.verifier import InstallVerifier


@dataclass(slots=True)
class InstallationPaths:
    source_path: Path
    destination_path: Path
    installed_game_path: Path


class InstallerService:
    def __init__(
        self,
        game_repository: GameRepository,
        planner: InstallPlanner | None = None,
        copier: InstallCopier | None = None,
        verifier: InstallVerifier | None = None,
        shortcut_service: ShortcutService | None = None,
    ) -> None:
        self._game_repository = game_repository
        self._planner = planner or InstallPlanner()
        self._copier = copier or InstallCopier()
        self._verifier = verifier or InstallVerifier()
        self._shortcut_service = shortcut_service or ShortcutService()

    def install_game(
        self,
        game: GameRecord,
        source_path: Path,
        install_root: Path,
        *,
        create_desktop_shortcut: bool = True,
        create_start_menu_shortcut: bool = False,
    ) -> InstallResult:
        paths = self._resolve_paths(game, source_path, install_root)
        source_relative_key = self._relative_source_key(game)
        plan = self._planner.create_plan(
            variant_key=game.variant_key,
            source_path=paths.source_path,
            install_root=install_root,
            source_relative_path=source_relative_key,
            executable_path=self._resolve_executable_path(game),
            install_emulator_with_games=game.install_emulator_with_games,
        )
        self._ensure_space(plan.source_path, install_root, plan.total_bytes)
        job_id = self._game_repository.upsert_install_job(
            game.variant_key,
            plan.source_path,
            plan.destination_path,
            "running",
            total_files=plan.total_files,
            total_bytes=plan.total_bytes,
        )
        self._game_repository.update_install_job(job_id, status="running")

        try:
            copy_result = self._copier.copy_tree(plan.source_path, plan.destination_path)
            verified, source_count, source_total, dest_count, dest_total = self._verifier.verify(
                plan.source_path,
                plan.destination_path,
            )
            install_status = "installed" if verified else "incomplete"
            installed_game_path = self._installed_game_path(game, paths.destination_path)
            executable_path = self._installed_executable_path(game, installed_game_path)
            shortcut_desktop_path = None
            shortcut_start_menu_path = None
            if verified and executable_path and create_desktop_shortcut:
                shortcut_desktop_path = str(
                    self._shortcut_service.create_shortcut(
                        self._desktop_shortcut_path(game),
                        executable_path,
                        self._shortcut_working_directory(game, installed_game_path),
                        self._shortcut_arguments(game, installed_game_path),
                    )
                )
            if verified and executable_path and create_start_menu_shortcut:
                shortcut_start_menu_path = str(
                    self._shortcut_service.create_shortcut(
                        self._start_menu_shortcut_path(game),
                        executable_path,
                        self._shortcut_working_directory(game, installed_game_path),
                        self._shortcut_arguments(game, installed_game_path),
                    )
                )
            installation_id = self._game_repository.upsert_installation(
                game.variant_key,
                installed_game_path,
                str(executable_path) if executable_path else None,
                install_status,
                source_file_count=source_count,
                source_total_size=source_total,
                dest_file_count=dest_count,
                dest_total_size=dest_total,
                shortcut_desktop_path=shortcut_desktop_path,
                shortcut_start_menu_path=shortcut_start_menu_path,
            )
            self._game_repository.update_install_job(
                job_id,
                status=install_status,
                copied_files=copy_result.copied_files,
                copied_bytes=copy_result.copied_bytes,
                current_file=None,
            )
            return InstallResult(
                job_id=job_id,
                installation_id=installation_id,
                status=install_status,
                shortcut_desktop_path=shortcut_desktop_path,
                shortcut_start_menu_path=shortcut_start_menu_path,
            )
        except Exception as exc:
            self._game_repository.update_install_job(job_id, status="failed", error_message=str(exc))
            raise

    def uninstall_game(self, game: GameRecord) -> None:
        installation = self._game_repository.get_installation(game.variant_key)
        if installation is None:
            return
        local_path = Path(installation["local_path"])
        if local_path.exists():
            shutil.rmtree(local_path)
        self._game_repository.remove_installation(game.variant_key)

    def verify_install(self, game: GameRecord) -> bool:
        installation = self._game_repository.get_installation(game.variant_key)
        if installation is None:
            return False
        local_path = Path(installation["local_path"])
        verified, source_count, source_total, dest_count, dest_total = self._verification_metrics(game, installation, local_path)
        self._game_repository.upsert_installation(
            game.variant_key,
            local_path,
            installation.get("executable_path"),
            "installed" if verified else "incomplete",
            source_file_count=source_count,
            source_total_size=source_total,
            dest_file_count=dest_count,
            dest_total_size=dest_total,
            shortcut_desktop_path=installation.get("shortcut_desktop_path"),
            shortcut_start_menu_path=installation.get("shortcut_start_menu_path"),
        )
        return verified

    def repair_install(self, game: GameRecord, source_path: Path, install_root: Path) -> InstallResult:
        return self.install_game(game, source_path, install_root)

    def _resolve_paths(self, game: GameRecord, source_path: Path, install_root: Path) -> InstallationPaths:
        if game.game_type == "emulated" and game.install_emulator_with_games:
            source_path = source_path.parent
        source_relative_path = self._relative_source_key(game)
        destination_path = self._destination_path_from_relative(source_relative_path, install_root)
        installed_game_path = self._installed_game_path(game, destination_path)
        return InstallationPaths(source_path=source_path, destination_path=destination_path, installed_game_path=installed_game_path)

    def _relative_source_key(self, game: GameRecord) -> str:
        if game.game_type == "emulated" and game.install_emulator_with_games:
            return str(Path(game.source_relative_path).parent).replace("\\", "/")
        return game.source_relative_path

    def _destination_path_from_relative(self, source_relative_path: str, install_root: Path) -> Path:
        parts = Path(source_relative_path).parts
        if parts and parts[0].lower() == "games":
            relative_parts = parts[1:]
        else:
            relative_parts = parts
        return install_root.joinpath(*relative_parts)

    def _installed_game_path(self, game: GameRecord, destination_path: Path) -> Path:
        if game.game_type == "emulated" and game.install_emulator_with_games:
            return destination_path / Path(game.source_relative_path).name
        return destination_path

    def _resolve_executable_path(self, game: GameRecord) -> str | None:
        if game.game_type == "pc":
            return game.executable_path
        return game.emulator_executable_path

    def _installed_executable_path(self, game: GameRecord, installed_game_path: Path) -> Path | None:
        if game.game_type == "pc":
            if game.executable_path:
                return installed_game_path / game.executable_path
            return None
        executable = game.emulator_executable_path
        if executable is None:
            return None
        if game.install_emulator_with_games:
            return installed_game_path.parent / executable
        return installed_game_path.parent / executable

    def _shortcut_working_directory(self, game: GameRecord, installed_game_path: Path) -> Path | None:
        if game.game_type == "pc":
            if game.working_directory:
                return installed_game_path / game.working_directory
            return installed_game_path
        if game.emulator_working_directory:
            return installed_game_path.parent / game.emulator_working_directory
        return installed_game_path.parent

    def _shortcut_arguments(self, game: GameRecord, installed_game_path: Path) -> str:
        if game.game_type == "pc":
            return game.launch_args
        rom_path = game.rom_path or ""
        emulator_args = game.emulator_launch_args or ""
        return emulator_args.replace("{rom_path}", str(installed_game_path / rom_path if rom_path else installed_game_path))

    def _desktop_shortcut_path(self, game: GameRecord) -> Path:
        return Path.home() / "Desktop" / f"{game.title}.lnk"

    def _start_menu_shortcut_path(self, game: GameRecord) -> Path:
        return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{game.title}.lnk"

    def _ensure_space(self, source_path: Path, install_root: Path, required_bytes: int) -> None:
        probe = install_root
        while not probe.exists() and probe.parent != probe:
            probe = probe.parent
        if not probe.exists():
            probe = Path.home()
        usage = shutil.disk_usage(probe)
        if usage.free < required_bytes:
            raise OSError(f"Insufficient disk space: need {required_bytes} bytes, have {usage.free}")

    def _source_for_verification(self, game: GameRecord, installation: dict, local_path: Path) -> Path:
        if game.game_type == "emulated" and game.install_emulator_with_games:
            return local_path.parent
        return Path(installation.get("local_path") or local_path)

    def _verification_metrics(
        self,
        game: GameRecord,
        installation: dict,
        local_path: Path,
    ) -> tuple[bool, int, int, int, int]:
        source_count = int(installation.get("source_file_count") or 0)
        source_total = int(installation.get("source_total_size") or 0)
        verified, dest_count, dest_total = self._verify_against_destination(local_path, source_count, source_total)
        return verified, source_count, source_total, dest_count, dest_total

    def _verify_against_destination(self, local_path: Path, source_count: int, source_total: int) -> tuple[bool, int, int]:
        destination_files = [path for path in local_path.rglob("*") if path.is_file()]
        dest_count = len(destination_files)
        dest_total = sum(path.stat().st_size for path in destination_files)
        if source_count and source_total:
            return source_count == dest_count and source_total == dest_total, dest_count, dest_total
        return dest_count > 0, dest_count, dest_total
