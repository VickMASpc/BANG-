from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CopyResult:
    copied_files: int
    copied_bytes: int
    total_files: int
    total_bytes: int


class InstallCopier:
    def copy_tree(self, source_path: Path, destination_path: Path) -> CopyResult:
        source_files = [path for path in sorted(source_path.rglob("*")) if path.is_file()]
        total_bytes = sum(path.stat().st_size for path in source_files)
        copied_files = 0
        copied_bytes = 0
        for source_file in source_files:
            relative = source_file.relative_to(source_path)
            destination_file = destination_path / relative
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            if destination_file.exists() and destination_file.stat().st_size == source_file.stat().st_size:
                continue
            shutil.copy2(source_file, destination_file)
            copied_files += 1
            copied_bytes += source_file.stat().st_size
        return CopyResult(
            copied_files=copied_files,
            copied_bytes=copied_bytes,
            total_files=len(source_files),
            total_bytes=total_bytes,
        )
