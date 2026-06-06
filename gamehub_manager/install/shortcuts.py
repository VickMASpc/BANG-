from __future__ import annotations

import subprocess
from pathlib import Path


class ShortcutError(RuntimeError):
    pass


class ShortcutService:
    def create_shortcut(
        self,
        shortcut_path: Path,
        target_path: Path,
        working_directory: Path | None = None,
        arguments: str = "",
        description: str = "GameHubDrive Manager shortcut",
    ) -> Path:
        shortcut_path.parent.mkdir(parents=True, exist_ok=True)
        if shortcut_path.suffix.lower() != ".lnk":
            shortcut_path = shortcut_path.with_suffix(".lnk")
        self._create_windows_shortcut(shortcut_path, target_path, working_directory, arguments, description)
        return shortcut_path

    @staticmethod
    def _create_windows_shortcut(
        shortcut_path: Path,
        target_path: Path,
        working_directory: Path | None,
        arguments: str,
        description: str,
    ) -> None:
        script = f"""
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut('{str(shortcut_path)}')
$shortcut.TargetPath = '{str(target_path)}'
$shortcut.WorkingDirectory = '{str(working_directory or target_path.parent)}'
$shortcut.Arguments = '{arguments.replace("'", "''")}'
$shortcut.Description = '{description.replace("'", "''")}'
$shortcut.Save()
"""
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise ShortcutError(completed.stderr.strip() or "Failed to create shortcut")
