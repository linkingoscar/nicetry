from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pytest

from app.services import process_ownership
from app.services.process_ownership import (
    get_process_commandline,
    is_process_owned_by_runtime,
    kill_process_tree,
)
from app.settings import Settings, get_settings


def _settings() -> Settings:
    return get_settings()


def test_owned_process_detected_case_insensitively() -> None:
    settings = _settings()
    commandline = str(settings.rscript_path).upper() + " --vanilla run.R"
    assert is_process_owned_by_runtime(
        4242, settings, commandline_reader=lambda _pid: commandline
    )
    assert not is_process_owned_by_runtime(
        4242, settings, commandline_reader=lambda _pid: "some-other-process.exe"
    )
    assert not is_process_owned_by_runtime(4242, settings, commandline_reader=lambda _pid: None)


def test_get_process_commandline_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(process_ownership.os, "name", "nt")
    monkeypatch.setattr(
        process_ownership.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(stdout="C:\\R\\Rscript.exe --vanilla\n"),
    )
    assert get_process_commandline(123) == "C:\\R\\Rscript.exe --vanilla"

    monkeypatch.setattr(
        process_ownership.subprocess,
        "run",
        lambda *_, **__: (_ for _ in ()).throw(OSError("cim unavailable")),
    )
    assert get_process_commandline(123) is None


def test_get_process_commandline_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(process_ownership.os, "name", "posix")
    monkeypatch.setattr(
        process_ownership.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(stdout="/opt/R/Rscript --vanilla\n"),
    )
    assert get_process_commandline(123) == "/opt/R/Rscript --vanilla"

    monkeypatch.setattr(
        process_ownership.subprocess,
        "run",
        lambda *_, **__: (_ for _ in ()).throw(OSError("ps unavailable")),
    )
    assert get_process_commandline(123) is None


def test_kill_process_tree_uses_taskkill_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, ...]] = []

    def fake_run(command: list[str], **_: object) -> None:
        calls.append(tuple(command))

    monkeypatch.setattr(process_ownership.subprocess, "run", fake_run)
    monkeypatch.setattr(process_ownership.os, "name", "nt")
    kill_process_tree(4242)
    assert calls[0][:5] == ("taskkill", "/F", "/T", "/PID", "4242")


def test_kill_process_tree_falls_back_to_process_kill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_run(command: list[str], **_: object) -> None:
        raise OSError("no taskkill")

    monkeypatch.setattr(process_ownership.subprocess, "run", fail_run)
    monkeypatch.setattr(process_ownership.os, "name", "nt")
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        kill_process_tree(process)
        assert process.wait(timeout=5) is not None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
