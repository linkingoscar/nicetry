from __future__ import annotations

from hmac import compare_digest
from threading import Lock


class SessionBootstrap:
    """Atomically exchange one launcher capability for the API session token."""

    def __init__(self, bootstrap_token: str, session_token: str) -> None:
        self._bootstrap_token = bootstrap_token
        self._session_token = session_token
        self._consumed = False
        self._lock = Lock()

    def exchange(self, supplied: str) -> str | None:
        with self._lock:
            if self._consumed or not compare_digest(supplied, self._bootstrap_token):
                return None
            self._consumed = True
            return self._session_token
