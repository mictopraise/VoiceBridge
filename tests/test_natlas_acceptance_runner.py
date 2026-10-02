import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from scripts.run_natlas_acceptance import run_acceptance


class FakePipeline:
    def __init__(self):
        self.model = SimpleNamespace(config=SimpleNamespace(_commit_hash="official-revision"))

    def __call__(self, payload):
        return {"text": "Mo fẹ́ ra foonu"}


class NAtlasAcceptanceRunnerTests(unittest.TestCase):
    def test_runner_uses_natlas_result_and_records_safe_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "yoruba.wav"
            with wave.open(str(audio), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(np.zeros(16000, dtype=np.int16).tobytes())
            output = root / "result.json"
            calls = []
            def loader(model_id, device):
                calls.append((model_id, device))
                return FakePipeline()
            report = run_acceptance(
                audio,
                output_path=output,
                pipeline_loader=loader,
                observation_probe=lambda: {"process_rss_bytes": 1},
                cache_root=root / "cache",
            )
            self.assertEqual(report["status"], "SUCCESS")
            self.assertEqual(calls, [("NCAIR1/Yoruba-ASR", -1)])
            self.assertEqual(report["model"]["revision"], "official-revision")
            self.assertEqual(report["asr_result"]["engine"], "natlas")
            self.assertIsNone(report["asr_result"]["metadata"]["confidence"])
            self.assertEqual(report["asr_result"]["segments"], [])
            self.assertTrue(report["assertions"]["no_whisper_fallback"])
            self.assertTrue(report["assertions"]["no_translation"])
            self.assertTrue(output.is_file())

    def test_runner_classifies_audio_input_failure_without_loading_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "bad.wav"
            audio.write_bytes(b"not wav")
            calls = []
            report = run_acceptance(
                audio,
                output_path=root / "result.json",
                pipeline_loader=lambda *args: calls.append(args),
                observation_probe=lambda: {},
                cache_root=root / "cache",
            )
            self.assertEqual(report["status"], "FAILED")
            self.assertEqual(report["failure"]["classification"], "audio-input issue")
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
