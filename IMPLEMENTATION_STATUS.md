# GameHubDrive Manager Implementation Status

## Implemented Areas
- App bootstrap creates `%APPDATA%\GameHubDriveManager\`, config, cache/log/thumbnail folders, and the SQLite DB.
- Drive detection now lists both initialized and non-initialized Windows drives containing or missing `GameHubDrive`.
- Drive initialization creates the required `GameHubDrive` folder layout and `drive.json`.
- Manifest scanning covers PC games, emulator games, missing manifests, invalid manifests, and launch-target validation.
- Config persistence now stores the chosen local install root in `config.json`.
- Database schema and repositories now cover games, installations, install jobs, launch sessions, and playtime.
- Installer pipeline exists with planning, copy/resume-style skipping, verification, shortcut creation, and uninstall support.
- Launcher pipeline exists for installed PC games and emulator profiles, with process tracking and playtime/session updates.
- UI wiring exists for selected-game actions, detected-drive display, install queue display, and initialization of invalid drives.
- A Windows packaging entry script exists: `build_windows_exe.py`.

## Missing Areas
- Full v1.0 install UX is not complete: no progress bar with speed/ETA/current-file rendering yet.
- Install pause/cancel/resume controls are not wired into the UI.
- Local library scanning of the install root is not yet a separate indexed sync pass; installed games are persisted through install operations and DB joins.
- Metadata editing, search, filtering, and richer library navigation are still minimal.
- Cover art loading is still placeholder-only.
- Emulator management is partial; v1 launch support exists, but full emulator installation policy and profile UX are still limited.
- Shortcut handling is Windows-only and uses a PowerShell COM path rather than a pywin32 abstraction.

## Proposed Module Additions
- `gamehub_manager/drives/initializer.py`
- `gamehub_manager/library/indexer.py`
- `gamehub_manager/library/resolver.py`
- `gamehub_manager/library/duplicates.py`
- `gamehub_manager/install/planner.py`
- `gamehub_manager/install/copier.py`
- `gamehub_manager/install/verifier.py`
- `gamehub_manager/install/jobs.py`
- `gamehub_manager/install/service.py`
- `gamehub_manager/install/shortcuts.py`
- `gamehub_manager/launch/launcher.py`
- `gamehub_manager/launch/process_tracker.py`
- `gamehub_manager/launch/emulator.py`
- `gamehub_manager/core/config.py`

## Test Strategy
- Existing unit and integration tests continue to pass.
- Added tests for config persistence, drive initialization, and install/verify copy flow.
- Remaining recommended tests:
  - emulator launch resolution
  - drive initialization UI hook
  - verify/repair behavior when source drive is disconnected
  - uninstall safety on installed local copies
  - manual Windows smoke tests for shortcut launch and external-drive removal

## Windows-Specific Isolation
- Drive enumeration, drive initialization, shortcut creation, `os.startfile`, and packaging entry are all isolated to dedicated modules or narrow UI handlers.
- The launcher and process tracker isolate Windows-specific process behavior behind `gamehub_manager/launch/`.
- The rest of the code remains file-system and data-model driven so the Windows-only assumptions stay localized.
