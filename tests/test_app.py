import io
import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np

import app as application


def wav_bytes(seconds=.1, rate=16000):
    buffer = io.BytesIO()
    samples = (np.sin(np.arange(int(rate * seconds)) / 8) * 10000).astype(np.int16)
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(samples.tobytes())
    buffer.seek(0)
    return buffer


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        application.app.config.update(TESTING=True)
        self.client = application.app.test_client()

    def test_application_import_and_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"VoiceBridge", response.data)

    def test_upload_is_required(self):
        response = self.client.post("/", data={})
        self.assertIn(b"Please choose", response.data)

    def test_unsupported_upload_is_rejected(self):
        response = self.client.post("/", data={"audio": (io.BytesIO(b"x"), "note.txt")})
        self.assertIn(b"Unsupported file", response.data)

    def test_reply_regeneration_requires_english_meaning(self):
        response = self.client.post("/suggest-reply", json={"english": ""})
        self.assertEqual(response.status_code, 400)

    def test_reply_regeneration_uses_edited_english(self):
        response = self.client.post("/suggest-reply", json={"english": "How much does it cost?"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("₦5,000", response.get_json()["reply"])

    def test_empty_action_regeneration_is_rejected(self):
        response = self.client.post("/analyze-action", json={})
        self.assertEqual(response.status_code, 400)

    def test_action_card_regeneration_endpoint(self):
        response = self.client.post("/analyze-action", json={
            "transcript": "Deliver two phones to Mokola tomorrow", "confidence": 90,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["action"]["intent"], "DELIVERY_REQUEST")

    def test_product_route_preserves_two_pass_whisper_provenance(self):
        calls = []
        def fake_run(path, task, language=None, model_size="small"):
            calls.append(task)
            if task == "transcribe":
                return "Abeg deliver two phones to Mokola", "en", 90, 90
            return "Please deliver two phones to Mokola", "en", 88, 90
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_whisper", side_effect=fake_run), \
             patch.object(application.os.path, "exists", return_value=False):
            response = self.client.post("/", data={"audio": (wav_bytes(), "note.wav")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, ["transcribe", "translate"])

    def test_low_confidence_upload_withholds_reply(self):
        outputs = [
            ("I want two phones", "en", 30, 90),
            ("I want two phones", "en", 30, 90),
        ]
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_whisper", side_effect=outputs), \
             patch.object(application.os.path, "exists", return_value=False):
            response = self.client.post("/", data={"audio": (wav_bytes(), "note.wav")})
        self.assertIn(b"Low confidence", response.data)


class AudioPreprocessingTests(unittest.TestCase):
    def test_preprocess_audio_outputs_normalized_mono_16khz_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.wav"
            source.write_bytes(wav_bytes(rate=8000).getvalue())
            output = application.preprocess_audio(str(source))
            try:
                with wave.open(output, "rb") as handle:
                    self.assertEqual(handle.getnchannels(), 1)
                    self.assertEqual(handle.getsampwidth(), 2)
                    self.assertEqual(handle.getframerate(), 16000)
            finally:
                if os.path.exists(output):
                    os.unlink(output)


if __name__ == "__main__":
    unittest.main()
