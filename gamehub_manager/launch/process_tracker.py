from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

try:
    import psutil
except ImportError:  # pragma: no cover - fallback for minimal environments
    psutil = None


@dataclass(slots=True)
class ProcessSessionResult:
    exit_code: int | None
    duration_seconds: int


class ProcessTracker:
    def wait_for_process_tree(self, pid: int, poll_interval: float = 0.5) -> ProcessSessionResult:
        start = time.monotonic()
        if psutil is None:
            return ProcessSessionResult(exit_code=None, duration_seconds=0)
        try:
            process = psutil.Process(pid)
        except psutil.Error:
            return ProcessSessionResult(exit_code=None, duration_seconds=0)
        exit_code: int | None = None
        while True:
            try:
                children = process.children(recursive=True)
            except psutil.Error:
                children = []
            alive_children = [child for child in children if child.is_running()]
            if process.is_running():
                try:
                    exit_code = process.wait(timeout=poll_interval)
                except psutil.TimeoutExpired:
                    pass
                except psutil.Error:
                    break
                else:
                    continue
            elif alive_children:
                time.sleep(poll_interval)
                continue
            else:
                break
            time.sleep(poll_interval)
        duration = int(time.monotonic() - start)
        return ProcessSessionResult(exit_code=exit_code, duration_seconds=duration)
