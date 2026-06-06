from __future__ import annotations

from pathlib import Path

from gamehub_manager.install.jobs import InstallPlan
from gamehub_manager.library.resolver import local_install_path


def _iter_files(root: Path) -> list[Path]:
    return [path for path in sorted(root.rglob("*")) if path.is_file()]


class InstallPlanner:
    def create_plan(
        self,
        variant_key: str,
        source_path: Path,
        install_root: Path,
        source_relative_path: str,
        executable_path: str | None = None,
        install_emulator_with_games: bool = False,
    ) -> InstallPlan:
        destination_path = local_install_path(install_root, source_relative_path)
        files = _iter_files(source_path)
        total_bytes = sum(path.stat().st_size for path in files)
        return InstallPlan(
            variant_key=variant_key,
            source_path=source_path,
            destination_path=destination_path,
            total_files=len(files),
            total_bytes=total_bytes,
            executable_path=executable_path,
            install_emulator_with_games=install_emulator_with_games,
        )
