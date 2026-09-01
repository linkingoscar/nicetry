from __future__ import annotations

import json
import os
import re
import shutil
import stat
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

JsonObject = dict[str, Any]


class UnsafePathError(ValueError):
    """Raised when persisted or imported path data is not an owned capability."""


_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def safe_relative_path(value: object, *, label: str = "path") -> Path:
    """Validate the portable relative-path representation stored in project state."""

    if not isinstance(value, str) or not value or "\x00" in value:
        raise UnsafePathError(f"{label} must be a non-empty path")
    if (
        "\\" in value
        or value.startswith("/")
        or value.startswith("~")
        or _WINDOWS_DRIVE.match(value)
    ):
        raise UnsafePathError(f"{label} must use a relative POSIX path")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise UnsafePathError(f"{label} escapes its owned root")
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise UnsafePathError(f"{label} escapes its owned root")
    return path


def safe_identifier(value: object, *, label: str = "identifier") -> str:
    """Validate identifiers before they are interpolated into owned paths."""

    if not isinstance(value, str) or not _SAFE_IDENTIFIER.fullmatch(value):
        raise UnsafePathError(f"{label} is not a safe identifier")
    return value


def is_link_or_reparse_point(path: Path) -> bool:
    """Reject POSIX links and Windows junction/reparse-point aliases."""

    try:
        metadata = path.lstat()
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    return path.is_symlink() or bool(attributes & reparse_flag)


def resolve_owned_path(
    state_root: Path,
    value: object,
    *,
    label: str = "path",
    expected_parent: Path | None = None,
    expected_name: str | None = None,
) -> Path:
    """Resolve a persisted path and prove containment and optional object binding."""

    relative = safe_relative_path(value, label=label)
    root = state_root.resolve()
    resolved = (root / relative).resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise UnsafePathError(f"{label} is outside the workspace")
    if expected_parent is not None:
        parent = expected_parent.resolve()
        if resolved.parent != parent:
            raise UnsafePathError(f"{label} is outside its expected object directory")
    if expected_name is not None and resolved.name != expected_name:
        raise UnsafePathError(f"{label} has an unexpected object name")
    return resolved


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


_utc_now = utc_now


def _write_json_atomic(path: Path, document: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        for attempt in range(20):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.01 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def read_json_safe(path: Path) -> JsonObject:
    for attempt in range(10):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.01)
    raise RuntimeError(f"Unable to read JSON document: {path}")


def remove_path_tree(path: Path, *, retries: int = 30, delay: float = 0.05) -> None:
    """Remove a directory tree, clearing Windows read-only attributes first.

    Dataset raw files are stored read-only (S_IREAD); on Windows such files
    make plain ``shutil.rmtree`` fail silently when callers pass
    ``ignore_errors=True``, leaving orphan directories behind.  Clear the
    attribute before every retry, then fall back to ignore_errors only after
    the retry budget is exhausted.
    """
    if not path.exists():
        return
    for attempt in range(retries):
        try:
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    os.chmod(os.path.join(root, name), stat.S_IWRITE)
                for name in dirs:
                    os.chmod(os.path.join(root, name), stat.S_IWRITE)
            shutil.rmtree(path)
            return
        except OSError:
            if attempt == retries - 1:
                break
            time.sleep(delay)
    shutil.rmtree(path, ignore_errors=True)


_read_json_safe = read_json_safe
