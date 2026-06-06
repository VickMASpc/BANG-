# GameHubDrive Manager

GameHubDrive Manager is a Windows-first PySide6 desktop application for managing game libraries stored on removable or external drives.

It detects compatible `GameHubDrive` volumes, initializes new drives safely, indexes PC and emulator-based games from manifests, persists library state in SQLite, and keeps installed games visible even when the source drive is disconnected.

## Current Status

This repository is an in-progress prototype aligned to the PRD in [PRD.txt](/C:/Users/Victor/Documents/BANG!/PRD.txt).

Implemented today:

- Windows-oriented app bootstrap with PySide6 desktop UI
- Drive detection and safe `GameHubDrive` initialization
- `drive.json` validation and non-crashing scan of malformed drives
- PC game and emulator game scanning from removable drives
- Emulator profile loading from `emulator.json`
- Library indexing, duplicate handling, stable `variant_key` generation, and `is_primary` assignment
- SQLite persistence for scanned games, installations, install jobs, launch sessions, and playtime
- Install, verify, repair, uninstall, and launch service layers
- Installed games remain visible after source-drive removal
- Automated test coverage with `pytest`

Still incomplete:

- Full search and filter UX in the main window
- Rich cover-art rendering beyond placeholder text
- Full install queue progress UX with speed, ETA, pause, cancel, and resume
- Metadata editing workflows
- Broader emulator-management UX

## Features

- Detects mounted drives that contain `GameHubDrive`
- Offers safe initialization for compatible candidate drives without formatting or deleting content
- Validates `drive.json` and required folder structure
- Scans:
  - `GameHubDrive/games/PC Games/<Game Title>/`
  - `GameHubDrive/games/Emulators/<Emulator Name>/<Game Name>/`
- Treats missing or invalid `game.json` as `Needs setup`
- Keeps invalid executable or ROM targets visible but not launchable
- Derives normalized IDs from folder names when a manifest omits `id`
- Generates stable `variant_key` values from source-relative paths
- Stores source-relative path, last seen drive root, launchability, and duplicate-primary state in SQLite
- Keeps local installation records queryable when the source drive is offline

## Required Drive Layout

Compatible drives use this structure:

```text
GameHubDrive/
  drive.json
  games/
    PC Games/
      <Game Title>/
        game.json
    Emulators/
      <Emulator Name>/
        emulator.json
        <Game Name>/
          game.json
  _imports/
  _logs/
```

The safe initializer creates only:

```text
GameHubDrive/
GameHubDrive/drive.json
GameHubDrive/games/
GameHubDrive/games/PC Games/
GameHubDrive/games/Emulators/
GameHubDrive/_imports/
GameHubDrive/_logs/
```

It never formats, erases, moves, or reorganizes existing drive contents.

## `drive.json` Schema

```json
{
  "schema_version": 1,
  "library_name": "GameHubDrive",
  "created_by": "GameHubDrive Manager",
  "notes": "",
  "folders": {
    "games": "games",
    "pc_games": "games/PC Games",
    "emulators": "games/Emulators"
  }
}
```

## Example Manifests

PC game:

```json
{
  "schema_version": 1,
  "id": "hollow-knight",
  "title": "Hollow Knight",
  "game_type": "pc",
  "genre": "Metroidvania",
  "version": "1.0",
  "executable_path": "Hollow Knight.exe",
  "launch_args": "",
  "working_directory": ".",
  "cover_image": "cover.jpg",
  "save_path": "saves"
}
```

Emulator profile:

```json
{
  "schema_version": 1,
  "emulator_id": "dolphin",
  "name": "Dolphin",
  "executable_path": "Dolphin.exe",
  "default_launch_args": "--batch --exec \"{rom_path}\"",
  "working_directory": "."
}
```

Emulator game:

```json
{
  "schema_version": 1,
  "id": "super-mario-galaxy",
  "title": "Super Mario Galaxy",
  "game_type": "emulated",
  "genre": "Platformer",
  "version": "1.0",
  "emulator_id": "dolphin",
  "rom_path": "Super Mario Galaxy.iso",
  "launch_args": "",
  "cover_image": "cover.jpg",
  "save_path": "../User"
}
```

## Architecture

Key packages:

- [gamehub_manager/app.py](/C:/Users/Victor/Documents/BANG!/gamehub_manager/app.py): application composition and refresh flow
- [gamehub_manager/drives/](/C:/Users/Victor/Documents/BANG!/gamehub_manager/drives): drive enumeration, validation, initialization, and source scanning
- [gamehub_manager/core/](/C:/Users/Victor/Documents/BANG!/gamehub_manager/core): shared constants, manifest parsing, models, paths, and config
- [gamehub_manager/library/](/C:/Users/Victor/Documents/BANG!/gamehub_manager/library): indexed library views, duplicate resolution, and UI-facing labels
- [gamehub_manager/db/](/C:/Users/Victor/Documents/BANG!/gamehub_manager/db): SQLite initialization, migrations, and repositories
- [gamehub_manager/install/](/C:/Users/Victor/Documents/BANG!/gamehub_manager/install): planning, copy, verification, shortcut creation, and install orchestration
- [gamehub_manager/launch/](/C:/Users/Victor/Documents/BANG!/gamehub_manager/launch): launch orchestration and playtime/session tracking
- [gamehub_manager/ui/](/C:/Users/Victor/Documents/BANG!/gamehub_manager/ui): PySide6 widgets and window wiring

## Data Model

The app stores its library in SQLite. Current tables:

- `settings`
- `games`
- `installations`
- `install_jobs`
- `launch_sessions`
- `playtime`

The `games` table persists:

- normalized `id`
- stable `variant_key`
- `source_relative_path`
- `source_drive_root_last_seen`
- `metadata_status`
- `is_launchable`
- `is_primary`
- emulator metadata
- installation and playtime state through joins

Migrations are idempotent and attempt to preserve older databases by creating missing tables, columns, and indexes.

## UI Overview

The current desktop UI includes:

- Left pane with library categories and detected drives
- Center table for indexed games
- Bottom install panel for recent jobs
- Right detail panel for selected-game actions

Available actions currently include:

- Initialize drive
- Install
- Launch
- Uninstall
- Repair
- Verify
- Open source folder
- Open install folder

## Requirements

- Windows
- Python 3.11+
- External drive access for real hardware testing

Runtime dependencies from [pyproject.toml](/C:/Users/Victor/Documents/BANG!/pyproject.toml):

- `PySide6>=6.7`
- `psutil>=5.9`

Development dependency:

- `pytest>=8.0`

## Setup

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

## Running the App

Start the desktop application:

```powershell
python -m gamehub_manager
```

The app bootstraps its application data under `%APPDATA%\GameHubDriveManager\`.

## Running Tests

```powershell
pytest
```

The current automated suite covers:

- path/bootstrap initialization
- drive detection and initialization
- PC and emulator scanning
- malformed metadata handling
- library persistence and offline-source behavior
- install and verify flow
- database migration safety

## Building a Windows Executable

There is a packaging helper script:

```powershell
python build_windows_exe.py
```

That script invokes PyInstaller against [gamehub_manager/__main__.py](/C:/Users/Victor/Documents/BANG!/gamehub_manager/__main__.py).

## Repository Layout

```text
gamehub_manager/
  core/
  db/
  drives/
  install/
  launch/
  library/
  ui/
tests/
PRD.txt
IMPLEMENTATION_STATUS.md
build_windows_exe.py
pyproject.toml
```

## Notes for Contributors

- Prefer `rg` for fast code search.
- Use `pytest` before finishing changes.
- The worktree may contain in-progress product iterations; avoid reverting unrelated edits.
- Windows-specific behavior should stay isolated in drives, launch, shortcut, and narrow UI modules.

## Roadmap

Near-term gaps from the PRD:

- richer filtering and search
- complete local-library sync beyond install-state joins
- better cover-art rendering
- fuller install-job UX
- metadata editing
- broader Windows smoke testing and packaging polish

## License

No license file is present in this repository yet. Treat the codebase as unlicensed until a license is added.
