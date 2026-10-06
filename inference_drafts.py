"""Short-lived, in-memory handoff for local inference review.

Drafts may contain transcripts, so they are deliberately never written to disk.
"""

from __future__ import annotations

from copy import deepcopy
import secrets
from threading import Lock
import time


class InferenceDraftStore:
    def __init__(self, ttl_seconds=1800, clock=None):
        self.ttl_seconds = ttl_seconds
        self._clock = clock or time.monotonic
        self._drafts = {}
        self._lock = Lock()

    def _purge(self):
        now = self._clock()
        expired = [
            token for token, item in self._drafts.items()
            if item["expires_at"] <= now
        ]
        for token in expired:
            self._drafts.pop(token, None)

    def create(self, payload):
        with self._lock:
            self._purge()
            token = secrets.token_urlsafe(24)
            self._drafts[token] = {
                "expires_at": self._clock() + self.ttl_seconds,
                "payload": deepcopy(payload),
            }
            return token

    def get(self, token):
        if not token:
            return None
        with self._lock:
            self._purge()
            item = self._drafts.get(token)
            return deepcopy(item["payload"]) if item else None

    def consume(self, token):
        if not token:
            return None
        with self._lock:
            self._purge()
            item = self._drafts.pop(token, None)
            return deepcopy(item["payload"]) if item else None

    def clear(self):
        with self._lock:
            self._drafts.clear()
