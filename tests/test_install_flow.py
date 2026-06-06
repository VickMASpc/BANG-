from __future__ import annotations

import json
from pathlib import Path

from gamehub_manager.core.config import ConfigStore
from gamehub_manager.core.models import DriveRecord
from gamehub_manager.db.database import Database
from gamehub_manager.db.repositories import GameRepository
from gamehub_manager.drives.initializer import DRIVE_JSON_PAYLOAD, DriveInitializer
from gamehub_manager.drives.scanner import LibraryScanner
from gamehub_manager.install.service import InstallerService


class DummyShortcutService:
    def create_shortcut(self, shortcut_path: Path, target_path: Path, working_directory: Path | None = None, arguments: str = "", description: str = "") -> Path:
        shortcut_path.parent.mkdir(parents=True, exist_ok=True)
        shortcut_path.write_text(f"{target_path}\n{working_directory}\n{arguments}\n{description}", encoding="utf-8")
        return shortcut_path


def test_config_store_roundtrip(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")
    store.set_install_root("D:/Games/GameHub")
    assert store.get_install_root() == "D:/Games/GameHub"


def test_drive_initializer_creates_expected_structure(tmp_path: Path) -> None:
    drive_root = tmp_path / "DriveE"
    drive_root.mkdir()

    result = DriveInitializer().initialize_drive(drive_root)

    created_relative_paths = {
        path.relative_to(drive_root).as_posix()
        for path in result.created_paths
    }
    assert created_relative_paths == {
        "GameHubDrive",
        "GameHubDrive/drive.json",
        "GameHubDrive/games",
        "GameHubDrive/games/PC Games",
        "GameHubDrive/games/Emulators",
        "GameHubDrive/_imports",
        "GameHubDrive/_logs",
    }
    assert json.loads((result.library_root / "drive.json").read_text(encoding="utf-8")) == DRIVE_JSON_PAYLOAD


def test_drive_initializer_preserves_preexisting_unrelated_files(tmp_path: Path) -> None:
    drive_root = tmp_path / "DriveF"
    drive_root.mkdir()
    unrelated_drive_file = drive_root / "keep.txt"
    unrelated_drive_file.write_text("keep", encoding="utf-8")

    library_root = drive_root / "GameHubDrive"
    library_root.mkdir()
    unrelated_library_file = library_root / "readme.txt"
    unrelated_library_file.write_text("keep", encoding="utf-8")

    DriveInitializer().initialize_drive(drive_root)

    assert unrelated_drive_file.read_text(encoding="utf-8") == "keep"
    assert unrelated_library_file.read_text(encoding="utf-8") == "keep"


def test_installer_copies_and_verifies_pc_game(fake_drive: Path, tmp_path: Path) -> None:
    game_dir = fake_drive / "games" / "PC Games" / "Hollow Knight"
    game_dir.mkdir(parents=True)
    (game_dir / "Hollow Knight.exe").write_text("binary", encoding="utf-8")
    (game_dir / "game.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Hollow Knight",
                "game_type": "pc",
                "executable_path": "Hollow Knight.exe",
            }
        ),
        encoding="utf-8",
    )

    database = Database(tmp_path / "gamehub.db")
    database.initialize()
    repository = GameRepository(database)
    scanner = LibraryScanner()
    drive = DriveRecord(
        drive_root=fake_drive.parent,
        library_root=fake_drive,
        drive_label="DriveE GameHubDrive",
        available=True,
        validation_status="valid",
    )
    game = scanner.scan_drive(drive)[0]
    repository.upsert_scan_results(drive, [game])

    installer = InstallerService(repository, shortcut_service=DummyShortcutService())
    install_root = tmp_path / "Games" / "GameHub"
    result = installer.install_game(game, game_dir, install_root)

    installation = repository.get_installation(game.variant_key)
    assert installation is not None
    assert installation["install_status"] == "installed"
    assert (Path(installation["local_path"]) / "Hollow Knight.exe").exists()
    assert result.status == "installed"
    assert result.shortcut_desktop_path is not None

    (Path(installation["local_path"]) / "Hollow Knight.exe").write_text("tampered", encoding="utf-8")
    assert installer.verify_install(game) is False
