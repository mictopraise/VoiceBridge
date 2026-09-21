"""Provider-neutral cache primitives for credit-protected remote ASR calls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from time import time
from typing import Any

from .base import ASRResult


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def request_cache_key(*, engine: str, model: str, audio_sha256: str, options: dict[str, Any] | None = None) -> str:
    identity = {"engine": engine, "model": model, "audio_sha256": audio_sha256, "options": options or {}}
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CacheIdentity:
    key: str
    audio_sha256: str
    engine: str
    model: str
    options: dict[str, Any]


class ProviderResultCache:
    """Persist successful raw/normalized results; never auto-retry failures."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def identity(self, audio_path: str | Path, *, engine: str, model: str, options: dict[str, Any] | None = None) -> CacheIdentity:
        audio_hash = sha256_file(audio_path)
        normalized_options = options or {}
        return CacheIdentity(
            key=request_cache_key(engine=engine, model=model, audio_sha256=audio_hash, options=normalized_options),
            audio_sha256=audio_hash, engine=engine, model=model, options=normalized_options,
        )

    def success_path(self, identity: CacheIdentity) -> Path:
        return self.root / "success" / f"{identity.key}.json"

    def load_success(self, identity: CacheIdentity) -> dict[str, Any] | None:
        path = self.success_path(identity)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_success(self, identity: CacheIdentity, *, raw_response: dict[str, Any], normalized_result: ASRResult) -> Path:
        path = self.success_path(identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return path
        payload = {
            "identity": asdict(identity), "saved_at_unix": time(),
            "raw_response": raw_response, "normalized_result": normalized_result.to_dict(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def record_failure(self, identity: CacheIdentity, *, error_type: str, error: str) -> Path:
        path = self.root / "failures.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "identity": asdict(identity), "recorded_at_unix": time(),
            "error_type": error_type, "error": error, "auto_retry": False,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return path
