"""Local adapter for the official NCAIR N-ATLAS ASR model repositories."""

from __future__ import annotations

import gc
from pathlib import Path
from time import perf_counter
from typing import Any, Callable
import wave

import numpy as np

from .base import ASRResult, EmptyTranscriptError, ProviderUnavailableError, SpeechEngineError


OFFICIAL_MODELS = {
    "yo": "NCAIR1/Yoruba-ASR",
    "en-NG": "NCAIR1/NigerianAccentedEnglish",
}


class NAtlasLanguageError(SpeechEngineError):
    """Raised when no official model is configured for the selected language."""


class NAtlasAudioFormatError(SpeechEngineError):
    """Raised when input is not the normalized WAV contract expected by the adapter."""


class NAtlasAudioTooLongError(SpeechEngineError):
    """Raised instead of silently truncating audio beyond the documented context."""


class NAtlasAccessError(ProviderUnavailableError):
    """Raised when gated official model files cannot be accessed."""


class NAtlasResponseError(SpeechEngineError):
    """Raised when the local Transformers pipeline returns an invalid response."""


class NAtlasInferenceError(SpeechEngineError):
    """Raised when local model inference fails."""


class NAtlasTaskError(SpeechEngineError):
    """Raised when a caller requests an undocumented N-ATLAS task."""


def normalize_language(language: str | None) -> str:
    value = (language or "").strip()
    if value.lower() == "yo":
        return "yo"
    if value.lower() in {"en-ng", "en_ng"}:
        return "en-NG"
    raise NAtlasLanguageError(
        "Select an officially supported N-ATLAS language: yo or en-NG. "
        "Nigerian Pidgin is not an official model in this adapter."
    )


def load_normalized_wav(audio_path: str | Path) -> tuple[np.ndarray, float]:
    """Read the existing VoiceBridge 16 kHz mono PCM WAV preprocessing output."""
    try:
        with wave.open(str(audio_path), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            frame_count = handle.getnframes()
            frames = handle.readframes(frame_count)
    except (wave.Error, EOFError, OSError) as exc:
        raise NAtlasAudioFormatError(
            "N-ATLAS requires a readable normalized WAV input."
        ) from exc
    if (channels, sample_width, sample_rate) != (1, 2, 16000):
        raise NAtlasAudioFormatError(
            "N-ATLAS requires VoiceBridge-normalized 16 kHz mono 16-bit PCM WAV audio."
        )
    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    duration = frame_count / sample_rate if sample_rate else 0.0
    return samples, duration


def _looks_like_access_failure(exc: Exception) -> bool:
    message = str(exc).casefold()
    markers = (
        "401", "403", "access", "authentication", "authorization",
        "forbidden", "gated", "login", "token", "unauthorized",
    )
    return any(marker in message for marker in markers)


def transformers_pipeline_factory(model_id: str, device: int | str):
    """Load an official model lazily; importing this module never imports Transformers."""
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise ProviderUnavailableError(
            "Local N-ATLAS dependencies are not installed. Install the declared requirements."
        ) from exc
    try:
        return pipeline("automatic-speech-recognition", model=model_id, device=device)
    except Exception as exc:
        if _looks_like_access_failure(exc):
            raise NAtlasAccessError(
                "The official gated N-ATLAS model could not be accessed. "
                "Accept its NCAIR Hugging Face terms and authenticate locally."
            ) from exc
        raise ProviderUnavailableError(
            f"The official N-ATLAS model could not be loaded ({type(exc).__name__})."
        ) from exc


class NAtlasEngine:
    """Run one explicitly selected official NCAIR ASR model at a time."""

    name = "natlas"
    model = "language-selected"

    def __init__(
        self,
        *,
        pipeline_factory: Callable[[str, int | str], Any] = transformers_pipeline_factory,
        audio_loader: Callable[[str | Path], tuple[np.ndarray, float]] = load_normalized_wav,
        device: int | str = -1,
        max_audio_seconds: float = 30.0,
    ):
        self._pipeline_factory = pipeline_factory
        self._audio_loader = audio_loader
        self.device = device
        self.max_audio_seconds = float(max_audio_seconds)
        self._pipeline = None
        self._loaded_model_id: str | None = None

    @property
    def loaded_model_id(self) -> str | None:
        return self._loaded_model_id

    def _get_pipeline(self, model_id: str):
        if self._pipeline is not None and self._loaded_model_id == model_id:
            return self._pipeline
        if self._pipeline is not None:
            self._pipeline = None
            self._loaded_model_id = None
            gc.collect()
        self._pipeline = self._pipeline_factory(model_id, self.device)
        self._loaded_model_id = model_id
        return self._pipeline

    def transcribe(
        self,
        audio_path: str,
        *,
        language: str | None = None,
        task: str = "transcribe",
    ) -> ASRResult:
        if task != "transcribe":
            raise NAtlasTaskError(
                "The official N-ATLAS ASR adapter supports transcription only; translation is separate."
            )
        selected_language = normalize_language(language)
        model_id = OFFICIAL_MODELS[selected_language]
        samples, audio_seconds = self._audio_loader(audio_path)
        if audio_seconds > self.max_audio_seconds:
            raise NAtlasAudioTooLongError(
                f"Audio is {audio_seconds:.3f} seconds; the documented N-ATLAS context limit "
                f"is {self.max_audio_seconds:.0f} seconds. Chunking is not enabled."
            )
        model_pipeline = self._get_pipeline(model_id)
        started = perf_counter()
        try:
            response = model_pipeline({"array": samples, "sampling_rate": 16000})
        except Exception as exc:
            raise NAtlasInferenceError(
                f"Local N-ATLAS inference failed ({type(exc).__name__})."
            ) from exc
        processing_seconds = perf_counter() - started
        if not isinstance(response, dict) or not isinstance(response.get("text"), str):
            raise NAtlasResponseError(
                "The N-ATLAS pipeline response must contain a text string."
            )
        transcript = response["text"].strip()
        if not transcript:
            raise EmptyTranscriptError("The N-ATLAS model returned an empty transcript.")
        device_label = "cpu" if self.device == -1 else str(self.device)
        return ASRResult(
            engine=self.name,
            model=model_id,
            transcript=transcript,
            detected_language=selected_language,
            segments=[],
            processing_seconds=processing_seconds,
            audio_seconds=audio_seconds,
            metadata={
                "provider": "NCAIR N-ATLAS",
                "official_repository": model_id,
                "selected_language": selected_language,
                "language_provenance": "explicit_user_or_caller_selection",
                "automatic_language_detection": False,
                "confidence": None,
                "segments_available": False,
                "timestamps_available": False,
                "translation_performed": False,
                "processing_seconds_source": "voicebridge_wall_clock",
                "runtime": "local_transformers",
                "device": device_label,
            },
        )
