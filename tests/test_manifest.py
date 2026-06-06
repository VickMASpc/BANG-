import json
from pathlib import Path

from gamehub_manager.core.manifest import build_variant_key, normalize_game_id, parse_game_folder


def test_normalize_game_id() -> None:
    assert normalize_game_id(" Hollow Knight: Silksong ") == "hollow-knight-silksong"


def test_parse_valid_pc_manifest(fake_drive: Path) -> None:
    game_dir = fake_drive / "games" / "PC Games" / "Hollow Knight"
    game_dir.mkdir(parents=True)
    (game_dir / "Hollow Knight.exe").write_text("", encoding="utf-8")
    (game_dir / "cover.jpg").write_text("", encoding="utf-8")
    (game_dir / "game.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Hollow Knight",
                "game_type": "pc",
                "executable_path": "Hollow Knight.exe",
                "cover_image": "cover.jpg",
                "save_path": "saves",
            }
        ),
        encoding="utf-8",
    )

    record = parse_game_folder(
        game_dir,
        game_dir.relative_to(fake_drive),
        "pc",
        fake_drive.parent,
    )

    assert record.title == "Hollow Knight"
    assert record.metadata_status == "ready"
    assert record.is_launchable is True
    assert record.cover_image_path is not None


def test_missing_manifest_becomes_needs_setup(fake_drive: Path) -> None:
    game_dir = fake_drive / "games" / "PC Games" / "Mystery Game"
    game_dir.mkdir(parents=True)

    record = parse_game_folder(
        game_dir,
        game_dir.relative_to(fake_drive),
        "pc",
        fake_drive.parent,
    )

    assert record.metadata_status == "needs_setup"
    assert record.is_launchable is False


def test_invalid_launch_target_stays_visible(fake_drive: Path) -> None:
    game_dir = fake_drive / "games" / "PC Games" / "Broken Game"
    game_dir.mkdir(parents=True)
    (game_dir / "game.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Broken Game",
                "game_type": "pc",
                "executable_path": "missing.exe",
            }
        ),
        encoding="utf-8",
    )

    record = parse_game_folder(
        game_dir,
        game_dir.relative_to(fake_drive),
        "pc",
        fake_drive.parent,
    )

    assert record.title == "Broken Game"
    assert record.metadata_status == "ready"
    assert record.is_launchable is False


def test_duplicate_folder_names_generate_distinct_variant_keys() -> None:
    first = build_variant_key(Path("games/PC Games/Doom"))
    second = build_variant_key(Path("games/Emulators/Dolphin/Doom"))

    assert first != second
