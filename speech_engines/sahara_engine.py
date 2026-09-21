"""Sahara adapter with offline normalization of preserved provider responses."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base import ASRResult, EmptyTranscriptError, ProviderUnavailableError
from .provider_cache import ProviderResultCache


class SaharaEngine:
    name = "sahara"
    model = "not-exposed"

    def __init__(self, *, credential_env: str = "VOICEBRIDGE_SAHARA_API_KEY", cache_dir: str | Path | None = None):
        self.credential_env = credential_env
        configured_cache = os.getenv("VOICEBRIDGE_SAHARA_CACHE_DIR")
        self.cache = ProviderResultCache(cache_dir or configured_cache or ".voicebridge-cache/sahara")

    def read_credential(self) -> str:
        credential = os.getenv(self.credential_env, "").strip()
        if not credential:
            raise ProviderUnavailableError(f"Sahara credential is missing from {self.credential_env}.")
        return credential

    def normalize_official_response(self, upload_response: dict[str, Any], *, status_response: dict[str, Any] | None = None, language: str | None = None) -> ASRResult:
        upload_data = upload_response.get("data") or {}
        final_response = status_response or upload_response
        final_data = final_response.get("data") or {}
        if not isinstance(upload_data, dict) or not isinstance(final_data, dict):
            raise ValueError("Sahara response 'data' must be an object.")
        final_status = str(final_data.get("processing_status") or "").strip()
        if final_status != "FILE_TRANSCRIBED":
            raise ProviderUnavailableError(f"Sahara result is not finalized: {final_status or 'status missing'}.")
        transcript = str(final_data.get("audio_transcript") or "").strip()
        if not transcript:
            raise EmptyTranscriptError("Finalized Sahara response has no transcript.")
        duration = final_data.get("processed_audio_duration_in_seconds")
        try:
            audio_seconds = float(duration) if duration is not None else 0.0
        except (TypeError, ValueError):
            audio_seconds = 0.0
        file_id = final_data.get("file_id") or upload_data.get("file_id")
        return ASRResult(
            engine=self.name, model=self.model, transcript=transcript,
            detected_language=language, processing_seconds=0.0,
            audio_seconds=audio_seconds,
            metadata={
                "provider": "Intron Sahara", "exact_model_version": None,
                "model_identity_note": "Not exposed by saved API response; documentation review required",
                "processing_status": final_status, "file_id": file_id,
                "audio_file_name": final_data.get("audio_file_name") or upload_data.get("audio_file_name"),
                "provider_message": final_response.get("message"),
                "provider_status": final_response.get("status"),
                "confidence": None, "provider_processing_seconds": None,
                "source": "saved_response",
            },
        )

    def transcribe(self, audio_path: str, *, language=None, task="transcribe"):
        raise ProviderUnavailableError(
            "Sahara is not configured. Add the official adapter only after API documentation and credentials are supplied."
        )
