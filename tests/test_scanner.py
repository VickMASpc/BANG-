import json
from pathlib import Path

from gamehub_manager.drives.detector import DriveDetector
from gamehub_manager.drives.scanner import LibraryScanner
from tests.helpers import create_fake_drive


def test_drive_detection_marks_valid_and_invalid_libraries(tmp_path: Path) -> None:
    valid_root = tmp_path / "DriveE"
    invalid_root = tmp_path / "DriveF"

    create_fake_drive(valid_root)
    (invalid_root / "GameHubDrive").mkdir(parents=True)

    detector = DriveDetector(drive_roots_provider=lambda: [valid_root, invalid_root])
    drives = detector.scan_drives()

    assert len(drives) == 2
    assert drives[0].available is True
    assert drives[1].validation_status == "invalid"


def test_library_scanner_loads_pc_and_emulated_games(fake_drive: Path) -> None:
    pc_dir = fake_drive / "games" / "PC Games" / "Celeste"
    pc_dir.mkdir(parents=True)
    (pc_dir / "Celeste.exe").write_text("", encoding="utf-8")
    (pc_dir / "game.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Celeste",
                "game_type": "pc",
                "executable_path": "Celeste.exe",
            }
        ),
        encoding="utf-8",
    )

    emulator_dir = fake_drive / "games" / "Emulators" / "Dolphin"
    mario_dir = emulator_dir / "Super Mario Galaxy"
    mario_dir.mkdir(parents=True)
    (emulator_dir / "emulator.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "emulator_id": "dolphin",
                "name": "Dolphin",
                "executable_path": "Dolphin.exe",
            }
        ),
        encoding="utf-8",
    )
    (mario_dir / "Super Mario Galaxy.iso").write_text("", encoding="utf-8")
    (mario_dir / "game.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Super Mario Galaxy",
                "game_type": "emulated",
                "rom_path": "Super Mario Galaxy.iso",
                "emulator_id": "dolphin",
            }
        ),
        encoding="utf-8",
    )

    detector = DriveDetector(drive_roots_provider=lambda: [fake_drive.parent])
    drives = detector.scan_drives()

    scanner = LibraryScanner()
    games = scanner.scan_drive(drives[0])

    assert {game.title for game in games} == {"Celeste", "Super Mario Galaxy"}
    assert {game.game_type for game in games} == {"pc", "emulated"}
