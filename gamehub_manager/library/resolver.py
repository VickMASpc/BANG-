from __future__ import annotations

from pathlib import Path
from typing import Mapping

from gamehub_manager.core.constants import PLACEHOLDER_COVER_TEXT


def source_relative_to_local_subpath(source_relative_path: str) -> Path:
    relative = Path(source_relative_path)
    parts = relative.parts
    if parts and parts[0].lower() == "games":
        return Path(*parts[1:])
    return relative


def local_install_path(install_root: Path, source_relative_path: str) -> Path:
    return install_root / source_relative_to_local_subpath(source_relative_path)


def resolve_cover_label(game: Mapping[str, object]) -> str:
    return str(game.get("cover_image_path") or PLACEHOLDER_COVER_TEXT)


def resolve_drive_status_label(game: Mapping[str, object]) -> str:
    return "Connected" if game.get("source_drive_root_last_seen") else "Source unavailable"


def resolve_install_status_label(game: Mapping[str, object]) -> str:
    if game.get("metadata_status") != "ready":
        return "Needs setup"

    install_status = str(game.get("install_status") or "").strip()
    if install_status:
        return install_status.replace("_", " ").title()

    return "Not installed"


def resolve_launch_target(game: Mapping[str, object]) -> str:
    return str(game.get("executable_path") or game.get("rom_path") or "")
