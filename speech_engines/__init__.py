"""Speech-provider registry. Benchmark mode never performs hidden fallback."""

from .base import ASRResult, EmptyTranscriptError, ProviderUnavailableError, SpeechEngineError


def create_engine(name: str, *, model: str = "large-v3"):
    normalized = name.strip().lower()
    if normalized == "whisper":
        from .whisper_engine import WhisperEngine
        return WhisperEngine(model=model)
    if normalized == "sahara":
        from .sahara_engine import SaharaEngine
        return SaharaEngine()
    if normalized == "model3":
        from .model3_engine import Model3Engine
        return Model3Engine()
    raise ProviderUnavailableError(f"Unknown speech engine: {name}")


def __getattr__(name: str):
    if name == "WhisperEngine":
        from .whisper_engine import WhisperEngine
        return WhisperEngine
    if name == "SaharaEngine":
        from .sahara_engine import SaharaEngine
        return SaharaEngine
    if name == "Model3Engine":
        from .model3_engine import Model3Engine
        return Model3Engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ASRResult", "EmptyTranscriptError", "ProviderUnavailableError",
    "SpeechEngineError", "WhisperEngine", "SaharaEngine", "Model3Engine",
    "create_engine",
]
