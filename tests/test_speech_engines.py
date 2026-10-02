import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from speech_engines import create_engine
from speech_engines.base import ASRResult, EmptyTranscriptError, ProviderUnavailableError
from speech_engines.provider_cache import ProviderResultCache
from speech_engines.sahara_engine import SaharaEngine
from speech_engines.whisper_engine import WhisperEngine


class ProviderRegistryTests(unittest.TestCase):
    def test_registry_constructs_whisper(self):
        self.assertIsInstance(create_engine("whisper", model="small"), WhisperEngine)

    def test_registry_constructs_sahara(self):
        self.assertIsInstance(create_engine("sahara"), SaharaEngine)

    def test_registry_rejects_unknown_provider(self):
        with self.assertRaises(ProviderUnavailableError):
            create_engine("unknown")


class SaharaNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.engine = SaharaEngine(cache_dir=tempfile.mkdtemp())
        self.upload = {"data": {"file_id": "file-1", "audio_file_name": "sample.wav"}}

    def test_finalized_saved_response_is_normalized(self):
        status = {"status": "success", "message": "done", "data": {
            "file_id": "file-1", "processing_status": "FILE_TRANSCRIBED",
            "audio_transcript": "Abeg deliver the phone", "processed_audio_duration_in_seconds": 4.2,
        }}
        result = self.engine.normalize_official_response(self.upload, status_response=status, language="pcm")
        self.assertEqual(result.engine, "sahara")
        self.assertEqual(result.transcript, "Abeg deliver the phone")
        self.assertEqual(result.detected_language, "pcm")
        self.assertIsNone(result.metadata["confidence"])

    def test_finalized_empty_transcript_is_terminal(self):
        status = {"data": {"processing_status": "FILE_TRANSCRIBED", "audio_transcript": ""}}
        with self.assertRaises(EmptyTranscriptError):
            self.engine.normalize_official_response(self.upload, status_response=status)

    def test_nonfinal_response_is_rejected(self):
        status = {"data": {"processing_status": "FILE_PROCESSING"}}
        with self.assertRaises(ProviderUnavailableError):
            self.engine.normalize_official_response(self.upload, status_response=status)


class ProviderCacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.audio = Path(self.directory.name) / "audio.wav"
        self.audio.write_bytes(b"same audio")
        self.cache = ProviderResultCache(Path(self.directory.name) / "cache")

    def tearDown(self):
        self.directory.cleanup()

    def test_cache_identity_is_deterministic_and_option_sensitive(self):
        first = self.cache.identity(self.audio, engine="sahara", model="x", options={"language": "pcm"})
        second = self.cache.identity(self.audio, engine="sahara", model="x", options={"language": "pcm"})
        changed = self.cache.identity(self.audio, engine="sahara", model="x", options={"language": "yo"})
        self.assertEqual(first.key, second.key)
        self.assertNotEqual(first.key, changed.key)

    def test_success_cache_round_trip(self):
        identity = self.cache.identity(self.audio, engine="sahara", model="x")
        result = ASRResult("sahara", "x", "hello", "pcm")
        self.cache.save_success(identity, raw_response={"ok": True}, normalized_result=result)
        loaded = self.cache.load_success(identity)
        self.assertEqual(loaded["normalized_result"]["transcript"], "hello")

    def test_failure_record_disables_automatic_retry(self):
        identity = self.cache.identity(self.audio, engine="sahara", model="x")
        path = self.cache.record_failure(identity, error_type="Timeout", error="failed")
        event = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        self.assertFalse(event["auto_retry"])


class FakeWhisperModel:
    def __init__(self, segments, language="yo", probability=.8):
        self.segments = segments
        self.info = SimpleNamespace(language=language, language_probability=probability)

    def transcribe(self, *args, **kwargs):
        return iter(self.segments), self.info


class WhisperAdapterTests(unittest.TestCase):
    def test_whisper_normalizes_model_output(self):
        segments = [SimpleNamespace(text=" hello ", start=0, end=1, avg_logprob=-.3)]
        engine = WhisperEngine(
            model="small", model_factory=lambda _: FakeWhisperModel(segments),
            duration_probe=lambda _: 1.0,
        )
        result = engine.transcribe("sample.wav", language="yo")
        self.assertEqual(result.transcript, "hello")
        self.assertEqual(result.model, "small")
        self.assertEqual(result.detected_language, "yo")
        self.assertEqual(len(result.segments), 1)

    def test_whisper_empty_transcript_is_terminal(self):
        engine = WhisperEngine(
            model_factory=lambda _: FakeWhisperModel([]), duration_probe=lambda _: 1.0
        )
        with self.assertRaises(EmptyTranscriptError):
            engine.transcribe("sample.wav")


if __name__ == "__main__":
    unittest.main()
