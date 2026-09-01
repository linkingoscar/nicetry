from __future__ import annotations

import io

from app.settings import Settings


class _Repository:
    def __init__(self, settings: Settings, dataset: dict[str, object] | None = None) -> None:
        self.settings = settings
        self._dataset = dataset

    def get_dataset(self, _dataset_id: str) -> dict[str, object]:
        assert self._dataset is not None
        return self._dataset

class _Process:
    def __init__(self, poll_values: list[int | None], stdout: str = "") -> None:
        self.pid = 4242
        self.returncode: int | None = None
        self.stdout = io.StringIO(stdout)
        self._poll_values = iter(poll_values)
        self.killed = False

    def poll(self) -> int | None:
        if self.returncode is not None:
            return self.returncode
        try:
            value = next(self._poll_values)
        except StopIteration:
            value = self.returncode
        if value is not None:
            self.returncode = value
        return value

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        if self.returncode is None:
            self.returncode = -9
        return self.returncode

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9
