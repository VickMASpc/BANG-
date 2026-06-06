import json
from pathlib import Path

from gamehub_manager.drives.detector import DriveDetector
from gamehub_manager.drives.scanner import LibraryScanner
from gamehub_manager.drives.initializer import DriveInitializer
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
    assert drives[0].validation_status == "valid"
    assert drives[1].validation_status == "invalid"
    assert "Missing drive.json" in drives[1].errors


def test_drive_with_missing_gamehubdrive_can_be_initialized(tmp_path: Path) -> None:
    drive_root = tmp_path / "DriveG"
    drive_root.mkdir()

    detector = DriveDetector(drive_roots_provider=lambda: [drive_root])
    before = detector.scan_drives()[0]
    assert before.validation_status == "missing"
    assert before.initializable is True

    DriveInitializer().initialize_drive(drive_root)

    after = detector.scan_drives()[0]
    assert after.available is True
    assert after.validation_status == "valid"


def test_malformed_drive_json_does_not_crash_scanning(tmp_path: Path) -> None:
    drive_root = tmp_path / "DriveH"
    library_root = create_fake_drive(drive_root)
    (library_root / "drive.json").write_text("{not-json", encoding="utf-8")

    detector = DriveDetector(drive_roots_provider=lambda: [drive_root])
    drives = detector.scan_drives()

    assert len(drives) == 1
    assert drives[0].available is False
    assert drives[0].validation_status == "invalid"
    assert any("Malformed drive.json" in error for error in drives[0].errors)


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
    mario = next(game for game in games if game.title == "Super Mario Galaxy")
    assert mario.emulator_id == "dolphin"
    assert mario.emulator_name == "Dolphin"
    assert mario.is_launchable is True
