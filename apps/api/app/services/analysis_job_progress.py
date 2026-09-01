from __future__ import annotations

import threading
import time
from typing import Callable, cast


def create_progress_callback(
    run_id: str,
    lock: threading.RLock,
    get_state: Callable[[str], dict[str, object]],
    save_state: Callable[[dict[str, object]], None],
) -> Callable[[dict[str, object]], None]:
    last_save_time = 0.0
    last_save_progress = -1.0
    last_save_stage = ""

    def progress(update: dict[str, object]) -> None:
        nonlocal last_save_time, last_save_progress, last_save_stage
        with lock:
            current = get_state(run_id)
            if current["status"] not in {"queued", "running", "cancelling"}:
                return
            stage = str(update.get("stage", current["stage"]))
            fraction = float(
                cast(str | float | int, update.get("progress", current["progress"]))
            )
            completed = int(
                cast(
                    str | float | int,
                    update.get("completedReplicates", current.get("completedReplicates", 0)),
                )
            )
            total = int(
                cast(str | float | int, update.get("totalReplicates", current.get("totalReplicates", 0)))
            )
            current.update(
                stage=stage,
                progress=fraction,
                completedReplicates=completed,
                totalReplicates=total,
            )
            now = time.monotonic()
            if (
                stage != last_save_stage
                or abs(fraction - last_save_progress) >= 0.05
                or now - last_save_time >= 2.0
                or fraction >= 1.0
            ):
                save_state(current)
                last_save_time = now
                last_save_progress = fraction
                last_save_stage = stage

    return progress
