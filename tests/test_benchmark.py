import json
import tempfile
import unittest
from pathlib import Path

from benchmark.manifest import ManifestError, load_manifest
from benchmark.metrics import cer, normalize_text, wer
from benchmark.run_asr_benchmark import run_asr_benchmark
from speech_engines.base import ASRResult, EmptyTranscriptError


class BenchmarkMetricTests(unittest.TestCase):
    def test_exact_speech_metrics_are_zero(self):
        self.assertEqual(wer("hello world", "hello world"), 0.0)
        self.assertEqual(cer("hello world", "hello world"), 0.0)

    def test_known_word_substitution(self):
        self.assertEqual(wer("one blue phone", "one black phone"), 1 / 3)

    def test_yoruba_diacritics_are_preserved(self):
        self.assertNotEqual(normalize_text("fẹ́"), normalize_text("fe"))
        self.assertGreater(cer("Mo fẹ́", "Mo fe"), 0)


class ManifestTests(unittest.TestCase):
    def test_duplicate_sample_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.jsonl"
            row = {"sample_id": "one", "audio_path": "a.wav", "reference_transcript": "hello"}
            path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaises(ManifestError):
                load_manifest(path)

    def test_missing_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.jsonl"
            path.write_text(json.dumps({"sample_id": "one", "audio_path": "a.wav"}) + "\n", encoding="utf-8")
            with self.assertRaises(ManifestError):
                load_manifest(path)


class FakeEngine:
    model = "fixture"

    def __init__(self, fail=False):
        self.fail = fail

    def transcribe(self, audio_path, language=None):
        if self.fail:
            raise EmptyTranscriptError("empty")
        return ASRResult("fixture", "fixture", "hello world", language, audio_seconds=1, processing_seconds=.5)


class BenchmarkRunnerTests(unittest.TestCase):
    def _fixture(self, directory):
        root = Path(directory)
        audio = root / "sample.wav"
        audio.write_bytes(b"fixture")
        manifest = root / "manifest.jsonl"
        manifest.write_text(json.dumps({
            "sample_id": "one", "audio_path": "sample.wav",
            "reference_transcript": "hello world", "dataset_config": "yoruba",
        }) + "\n", encoding="utf-8")
        return manifest

    def test_asr_benchmark_writes_machine_readable_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._fixture(directory)
            output = Path(directory) / "results"
            rows = run_asr_benchmark(
                manifest, output, model="fixture",
                engine_factory=lambda *args, **kwargs: FakeEngine(),
            )
            self.assertEqual(rows[0]["status"], "succeeded")
            self.assertTrue((output / "raw_results.jsonl").is_file())
            self.assertTrue((output / "model_summary.csv").is_file())
            self.assertTrue((output / "language_summary.csv").is_file())

    def test_provider_failure_remains_in_attempted_results(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._fixture(directory)
            rows = run_asr_benchmark(
                manifest, Path(directory) / "results", model="fixture",
                engine_factory=lambda *args, **kwargs: FakeEngine(fail=True),
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "failed")
            self.assertEqual(rows[0]["error_type"], "EmptyTranscriptError")


if __name__ == "__main__":
    unittest.main()
