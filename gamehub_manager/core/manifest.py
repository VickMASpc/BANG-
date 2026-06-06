from __future__ import annotations

import json
import re
from pathlib import Path

from gamehub_manager.core.constants import GAME_MANIFEST_NAME
from gamehub_manager.core.errors import ManifestError
from gamehub_manager.core.models import GameRecord


def normalize_game_id(raw_name: str) -> str:
    normalized = raw_name.strip().lower()
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"[^a-z0-9._-]", "", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized)
    normalized = normalized.strip("-")
    return normalized or "unknown-game"


def build_variant_key(source_relative_path: Path) -> str:
    normalized_parts = [normalize_game_id(part) for part in source_relative_path.parts]
    return "/".join(part for part in normalized_parts if part)


def parse_json_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(str(exc)) from exc


def compute_directory_size(path: Path) -> int:
    total_size = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total_size += child.stat().st_size
            except OSError:
                continue
    return total_size


def parse_game_folder(
    game_folder: Path,
    source_relative_path: Path,
    expected_type: str,
    drive_root: Path,
) -> GameRecord:
    manifest_path = game_folder / GAME_MANIFEST_NAME
    title_fallback = game_folder.name
    source_relative = source_relative_path.as_posix()
    variant_key = build_variant_key(source_relative_path)
    cover_image_path: str | None = None
    executable_path: str | None = None
    rom_path: str | None = None
    save_path: str | None = None
    working_directory: str | None = None
    launch_args = ""
    notes = ""
    metadata_status = "ready"
    game_type = expected_type
    genre = ""
    version = ""
    emulator_id: str | None = None

    if not manifest_path.exists():
        metadata_status = "needs_setup"
        title = title_fallback
    else:
        try:
            manifest = parse_json_file(manifest_path)
        except ManifestError as exc:
            manifest = {}
            metadata_status = "needs_setup"
            title = title_fallback
            notes = f"Invalid manifest: {exc}"
        else:
            title = str(manifest.get("title") or title_fallback)
            game_type = str(manifest.get("game_type") or expected_type)
            genre = str(manifest.get("genre") or "")
            version = str(manifest.get("version") or "")
            executable_path = manifest.get("executable_path")
            rom_path = manifest.get("rom_path")
            save_path = manifest.get("save_path")
            working_directory = manifest.get("working_directory")
            launch_args = str(manifest.get("launch_args") or "")
            emulator_id = manifest.get("emulator_id")
            if not manifest.get("schema_version") or not manifest.get("game_type"):
                metadata_status = "needs_setup"
            cover_name = manifest.get("cover_image")
            if cover_name:
                candidate_cover = game_folder / cover_name
                if candidate_cover.exists():
                    cover_image_path = str(candidate_cover)
            title_id = str(manifest.get("id") or normalize_game_id(title_fallback))
            id_value = normalize_game_id(title_id)
            is_launchable = _resolve_launchable(game_folder, game_type, executable_path, rom_path)
            if not is_launchable and metadata_status == "ready":
                notes = "Launch target is missing."
            return GameRecord(
                id=id_value,
                variant_key=variant_key,
                title=title,
                game_type=game_type,
                genre=genre,
                version=version,
                source_type="drive",
                source_relative_path=source_relative,
                source_drive_root_last_seen=str(drive_root),
                manifest_path_last_seen=str(manifest_path),
                cover_image_path=cover_image_path,
                metadata_status=metadata_status,
                is_launchable=is_launchable,
                executable_path=executable_path,
                rom_path=rom_path,
                save_path=save_path,
                working_directory=working_directory,
                launch_args=launch_args,
                size_bytes=compute_directory_size(game_folder),
                emulator_id=emulator_id,
                notes=notes,
            )

    return GameRecord(
        id=normalize_game_id(title_fallback),
        variant_key=variant_key,
        title=title_fallback if metadata_status == "needs_setup" else title,
        game_type=expected_type,
        genre=genre,
        version=version,
        source_type="drive",
        source_relative_path=source_relative,
        source_drive_root_last_seen=str(drive_root),
        manifest_path_last_seen=str(manifest_path) if manifest_path.exists() else None,
        cover_image_path=cover_image_path,
        metadata_status=metadata_status,
        is_launchable=False,
        executable_path=executable_path,
        rom_path=rom_path,
        save_path=save_path,
        working_directory=working_directory,
        launch_args=launch_args,
        size_bytes=compute_directory_size(game_folder),
        emulator_id=emulator_id,
        notes=notes,
    )


def _resolve_launchable(
    game_folder: Path,
    game_type: str,
    executable_path: str | None,
    rom_path: str | None,
) -> bool:
    if game_type == "pc":
        return bool(executable_path and (game_folder / executable_path).exists())
    if game_type == "emulated":
        return bool(rom_path and (game_folder / rom_path).exists())
    return False
