import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from speech_engines import create_engine
from speech_engines.base import EmptyTranscriptError, ProviderUnavailableError
from speech_engines.natlas_engine import (
    NAtlasAccessError,
    NAtlasAudioFormatError,
    NAtlasAudioTooLongError,
    NAtlasEngine,
    NAtlasInferenceError,
    NAtlasLanguageError,
    NAtlasResponseError,
    NAtlasTaskError,
    OFFICIAL_MODELS,
    load_normalized_wav,
    transformers_pipeline_factory,
)


class PipelineRecorder:
    def __init__(self, response=None, error=None):
        self.response = response if response is not None else {"text": "Mo fẹ́ ra foonu méjì"}
        self.error = error
        self.calls = []

    def __call__(self, payload):
        self.calls.append(payload)
        if self.error:
            raise self.error
        return self.response


class FactoryRecorder:
    def __init__(self, pipeline=None, error=None):
        self.pipeline = pipeline or PipelineRecorder()
        self.error = error
        self.calls = []

    def __call__(self, model_id, device):
        self.calls.append((model_id, device))
        if self.error:
            raise self.error
        return self.pipeline


def fixed_audio(seconds=2.0):
    return np.zeros(int(16000 * seconds), dtype=np.float32), seconds


class NAtlasMappingTests(unittest.TestCase):
    def test_yoruba_mapping_uses_official_repository(self):
        self.assertEqual(OFFICIAL_MODELS["yo"], "NCAIR1/Yoruba-ASR")

    def test_nigerian_english_mapping_uses_official_repository(self):
        self.assertEqual(OFFICIAL_MODELS["en-NG"], "NCAIR1/NigerianAccentedEnglish")

    def test_registry_constructs_natlas_without_loading_a_model(self):
        engine = create_engine("natlas")
        self.assertIsInstance(engine, NAtlasEngine)
        self.assertIsNone(engine.loaded_model_id)

    def test_pidgin_and_unconfigured_languages_are_rejected(self):
        engine = NAtlasEngine(audio_loader=lambda _: fixed_audio())
        for language in ("pcm", "pidgin", "ha", "ig", "en", None):
            with self.subTest(language=language):
                with self.assertRaises(NAtlasLanguageError):
                    engine.transcribe("fixture.wav", language=language)


class NAtlasResultTests(unittest.TestCase):
    def test_successful_transcription_normalizes_truthful_provenance(self):
        pipeline = PipelineRecorder({"text": "  Mo fẹ́ ra foonu méjì  "})
        factory = FactoryRecorder(pipeline)
        engine = NAtlasEngine(pipeline_factory=factory, audio_loader=lambda _: fixed_audio(3.0))
        result = engine.transcribe("fixture.wav", language="yo")
        self.assertEqual(result.engine, "natlas")
        self.assertEqual(result.model, "NCAIR1/Yoruba-ASR")
        self.assertEqual(result.transcript, "Mo fẹ́ ra foonu méjì")
        self.assertEqual(result.detected_language, "yo")
        self.assertEqual(result.audio_seconds, 3.0)
        self.assertGreaterEqual(result.processing_seconds, 0.0)
        self.assertEqual(result.segments, [])
        self.assertIsNone(result.metadata["confidence"])
        self.assertFalse(result.metadata["automatic_language_detection"])
        self.assertEqual(result.metadata["language_provenance"], "explicit_user_or_caller_selection")
        self.assertFalse(result.metadata["translation_performed"])
        self.assertEqual(len(pipeline.calls), 1)
        self.assertEqual(pipeline.calls[0]["sampling_rate"], 16000)

    def test_nigerian_english_result_records_selected_language(self):
        engine = NAtlasEngine(
            pipeline_factory=FactoryRecorder(PipelineRecorder({"text": "I need two phones"})),
            audio_loader=lambda _: fixed_audio(),
        )
        result = engine.transcribe("fixture.wav", language="en-ng")
        self.assertEqual(result.model, "NCAIR1/NigerianAccentedEnglish")
        self.assertEqual(result.detected_language, "en-NG")
        self.assertEqual(result.metadata["selected_language"], "en-NG")

    def test_empty_transcription_is_terminal(self):
        engine = NAtlasEngine(
            pipeline_factory=FactoryRecorder(PipelineRecorder({"text": "   "})),
            audio_loader=lambda _: fixed_audio(),
        )
        with self.assertRaises(EmptyTranscriptError):
            engine.transcribe("fixture.wav", language="yo")

    def test_malformed_pipeline_responses_are_rejected(self):
        for response in (None, [], {}, {"text": None}, {"text": 42}):
            with self.subTest(response=response):
                pipeline = PipelineRecorder()
                pipeline.response = response
                engine = NAtlasEngine(
                    pipeline_factory=FactoryRecorder(pipeline),
                    audio_loader=lambda _: fixed_audio(),
                )
                with self.assertRaises(NAtlasResponseError):
                    engine.transcribe("fixture.wav", language="yo")

    def test_translation_task_is_explicitly_out_of_scope(self):
        engine = NAtlasEngine(audio_loader=lambda _: fixed_audio())
        with self.assertRaises(NAtlasTaskError):
            engine.transcribe("fixture.wav", language="yo", task="translate")


class NAtlasFailureTests(unittest.TestCase):
    def test_factory_maps_gated_authentication_failure(self):
        fake_transformers = SimpleNamespace(
            pipeline=lambda *args, **kwargs: (_ for _ in ()).throw(
                OSError("401 gated repository; token required")
            )
        )
        with patch.dict(sys.modules, {"transformers": fake_transformers}):
            with self.assertRaises(NAtlasAccessError):
                transformers_pipeline_factory("NCAIR1/Yoruba-ASR", -1)

    def test_factory_maps_generic_load_failure_without_leaking_details(self):
        fake_transformers = SimpleNamespace(
            pipeline=lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("sensitive local cache path")
            )
        )
        with patch.dict(sys.modules, {"transformers": fake_transformers}):
            with self.assertRaisesRegex(ProviderUnavailableError, "RuntimeError") as caught:
                transformers_pipeline_factory("NCAIR1/Yoruba-ASR", -1)
        self.assertNotIn("sensitive local cache path", str(caught.exception))

    def test_model_load_failure_remains_provider_failure(self):
        engine = NAtlasEngine(
            pipeline_factory=FactoryRecorder(error=ProviderUnavailableError("load failed")),
            audio_loader=lambda _: fixed_audio(),
        )
        with self.assertRaises(ProviderUnavailableError):
            engine.transcribe("fixture.wav", language="yo")

    def test_gated_access_failure_remains_explicit(self):
        engine = NAtlasEngine(
            pipeline_factory=FactoryRecorder(error=NAtlasAccessError("gated")),
            audio_loader=lambda _: fixed_audio(),
        )
        with self.assertRaises(NAtlasAccessError):
            engine.transcribe("fixture.wav", language="yo")

    def test_inference_exception_is_controlled(self):
        engine = NAtlasEngine(
            pipeline_factory=FactoryRecorder(PipelineRecorder(error=RuntimeError("device failure"))),
            audio_loader=lambda _: fixed_audio(),
        )
        with self.assertRaises(NAtlasInferenceError):
            engine.transcribe("fixture.wav", language="yo")

    def test_over_limit_audio_is_rejected_before_model_load(self):
        factory = FactoryRecorder()
        engine = NAtlasEngine(pipeline_factory=factory, audio_loader=lambda _: fixed_audio(30.001))
        with self.assertRaises(NAtlasAudioTooLongError):
            engine.transcribe("fixture.wav", language="yo")
        self.assertEqual(factory.calls, [])

    def test_failure_never_invokes_whisper_fallback(self):
        engine = NAtlasEngine(
            pipeline_factory=FactoryRecorder(PipelineRecorder(error=RuntimeError("fail"))),
            audio_loader=lambda _: fixed_audio(),
        )
        with patch("speech_engines.whisper_engine.WhisperEngine.transcribe") as whisper:
            with self.assertRaises(NAtlasInferenceError):
                engine.transcribe("fixture.wav", language="yo")
            whisper.assert_not_called()


class NAtlasLoadingTests(unittest.TestCase):
    def test_model_loading_is_lazy(self):
        factory = FactoryRecorder()
        engine = NAtlasEngine(pipeline_factory=factory, audio_loader=lambda _: fixed_audio())
        self.assertEqual(factory.calls, [])
        self.assertIsNone(engine.loaded_model_id)

    def test_same_model_is_reused_within_process(self):
        factory = FactoryRecorder()
        engine = NAtlasEngine(pipeline_factory=factory, audio_loader=lambda _: fixed_audio())
        engine.transcribe("first.wav", language="yo")
        engine.transcribe("second.wav", language="yo")
        self.assertEqual(factory.calls, [("NCAIR1/Yoruba-ASR", -1)])

    def test_switching_language_replaces_the_active_model(self):
        factory = FactoryRecorder()
        engine = NAtlasEngine(pipeline_factory=factory, audio_loader=lambda _: fixed_audio())
        engine.transcribe("first.wav", language="yo")
        engine.transcribe("second.wav", language="en-NG")
        self.assertEqual(len(factory.calls), 2)
        self.assertEqual(engine.loaded_model_id, "NCAIR1/NigerianAccentedEnglish")


class NormalizedWavTests(unittest.TestCase):
    def test_normalized_wav_loader_preserves_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.wav"
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(np.zeros(8000, dtype=np.int16).tobytes())
            samples, duration = load_normalized_wav(path)
            self.assertEqual(len(samples), 8000)
            self.assertEqual(duration, 0.5)

    def test_non_normalized_wav_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.wav"
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(8000)
                handle.writeframes(np.zeros(8000, dtype=np.int16).tobytes())
            with self.assertRaises(NAtlasAudioFormatError):
                load_normalized_wav(path)


if __name__ == "__main__":
    unittest.main()
