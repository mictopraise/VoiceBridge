"""Provider-independent speech recognition contract for VoiceBridge."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


class SpeechEngineError(RuntimeError):
    """Base exception for a speech engine failure."""


class ProviderUnavailableError(SpeechEngineError):
    """Raised when a requested provider has not been configured."""


class EmptyTranscriptError(SpeechEngineError):
    """Raised when an engine completes without recognizable speech."""


@dataclass(frozen=True)
class ASRSegment:
    start: float
    end: float
    text: str
    confidence: float | None = None


@dataclass(frozen=True)
class ASRResult:
    engine: str
    model: str
    transcript: str
    detected_language: str | None
    segments: list[ASRSegment] = field(default_factory=list)
    processing_seconds: float = 0.0
    audio_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SpeechEngine(ABC):
    name: str
    model: str

    @abstractmethod
    def transcribe(self, audio_path: str, *, language: str | None = None, task: str = "transcribe") -> ASRResult:
        """Return one normalized result or raise a declared engine error."""
