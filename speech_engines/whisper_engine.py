"""faster-whisper adapter implementing the VoiceBridge ASR contract."""

from __future__ import annotations

from time import perf_counter
from typing import Callable

import av
from faster_whisper import WhisperModel

from .base import ASRResult, ASRSegment, EmptyTranscriptError


def audio_duration_seconds(audio_path: str) -> float:
    with av.open(audio_path) as container:
        if container.duration is not None:
            return max(0.0, float(container.duration / av.time_base))
        stream = next((item for item in container.streams if item.type == "audio"), None)
        if stream and stream.duration is not None and stream.time_base is not None:
            return max(0.0, float(stream.duration * stream.time_base))
    return 0.0


class WhisperEngine:
    name = "whisper"

    def __init__(self, model: str = "large-v3", *, model_factory: Callable[[str], WhisperModel] | None = None, duration_probe: Callable[[str], float] = audio_duration_seconds):
        self.model = model
        self._model_factory = model_factory or (lambda size: WhisperModel(size, device="cpu", compute_type="int8"))
        self._duration_probe = duration_probe
        self._loaded_model = None

    def _get_model(self):
        if self._loaded_model is None:
            self._loaded_model = self._model_factory(self.model)
        return self._loaded_model

    def transcribe(self, audio_path: str, *, language: str | None = None, task: str = "transcribe") -> ASRResult:
        audio_seconds = self._duration_probe(audio_path)
        model = self._get_model()
        started = perf_counter()
        segments, info = model.transcribe(
            audio_path, task=task, language=language, beam_size=5, vad_filter=True,
            condition_on_previous_text=False, no_speech_threshold=0.5,
            compression_ratio_threshold=2.2,
        )
        segment_list = list(segments)
        transcript = " ".join(item.text.strip() for item in segment_list if item.text.strip()).strip()
        processing_seconds = perf_counter() - started
        if not transcript:
            raise EmptyTranscriptError("The speech engine returned an empty transcript.")
        speech_segments = [item for item in segment_list if item.text.strip()]
        avg_logprob = sum(item.avg_logprob for item in speech_segments) / len(speech_segments)
        confidence = max(0, min(100, round((avg_logprob + 1.5) / 1.5 * 100)))
        language_probability = round(float(getattr(info, "language_probability", 0.0)) * 100)
        normalized_segments = [
            ASRSegment(
                start=float(item.start), end=float(item.end), text=item.text.strip(),
                confidence=max(0.0, min(1.0, (float(item.avg_logprob) + 1.5) / 1.5)),
            )
            for item in speech_segments
        ]
        return ASRResult(
            engine=self.name, model=self.model, transcript=transcript,
            detected_language=getattr(info, "language", language),
            segments=normalized_segments, processing_seconds=processing_seconds,
            audio_seconds=audio_seconds,
            metadata={
                "task": task, "confidence": confidence,
                "language_probability": language_probability,
                "forced_language": language, "runtime": "faster-whisper",
            },
        )
