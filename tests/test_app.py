import io
import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np

import app as application
from speech_engines.base import ASRResult, ProviderUnavailableError
from speech_engines.natlas_engine import NAtlasAudioTooLongError


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
        self.directory = tempfile.TemporaryDirectory()
        application.app.config.update(
            TESTING=True,
            FIELD_TEST_LOG_PATH=str(Path(self.directory.name) / "interactions.json"),
            FIELD_TEST_PROCESSING_INDEX_PATH=str(Path(self.directory.name) / "processed.json"),
        )
        application._inference_drafts.clear()
        self.client = application.app.test_client()

    def tearDown(self):
        self.directory.cleanup()

    def test_application_import_and_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"VoiceBridge", response.data)
        self.assertIn(b"N-ATLAS", response.data)
        self.assertIn("Fast — Yoruba".encode(), response.data)
        self.assertIn("Fast — Nigerian English".encode(), response.data)
        self.assertIn("Double-check — Run both N-ATLAS models".encode(), response.data)
        self.assertIn("Whisper — Explicit alternative".encode(), response.data)
        labels = [
            "Fast — Yoruba", "Fast — Nigerian English",
            "Double-check — Run both N-ATLAS models", "Whisper — Explicit alternative",
        ]
        positions = [response.data.index(label.encode()) for label in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertIn(b'<option value="natlas_en" selected>', response.data)
        self.assertNotIn(b'<option value="dual_natlas" selected>', response.data)

    def test_one_upload_invokes_both_natlas_models_and_keeps_outputs_separate(self):
        outputs = [
            self._natlas_result("YORUBA IMMUTABLE OUTPUT"),
            ASRResult("natlas", "NCAIR1/NigerianAccentedEnglish",
                      "ENGLISH IMMUTABLE OUTPUT", "en-NG", metadata={"confidence": None}),
        ]
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas", side_effect=outputs) as natlas, \
             patch.object(application, "run_whisper") as whisper, \
             patch.object(application.os.path, "exists", return_value=False):
            response = self._post_audio(provider="dual_natlas", language="dual")
        self.assertEqual([call.args[1] for call in natlas.call_args_list], ["yo", "en-NG"])
        whisper.assert_not_called()
        self.assertIn(b"YORUBA IMMUTABLE OUTPUT", response.data)
        self.assertIn(b"ENGLISH IMMUTABLE OUTPUT", response.data)
        self.assertIn(b"human review required", response.data.lower())
        self.assertNotIn(b"automatically correct", response.data.lower())
        self.assertIn(b"Choose a model output to begin human review", response.data)
        self.assertIn(b'id="action-card" class="result action-card" style="display:none"', response.data)
        self.assertIn(b'id="log-field-test"', response.data)
        self.assertIn(b"disabled", response.data)
        self.assertIn(b"chooseStartingTranscriptFromButton(this)", response.data)

    def test_dual_start_selection_refreshes_action_and_handles_language(self):
        response = self.client.get("/")
        self.assertIn(b"async function chooseStartingTranscript", response.data)
        self.assertIn(b"await regenerateAction()", response.data)
        self.assertIn(b"language==='en-NG'?transcript:''", response.data)
        self.assertIn(b"No English meaning was invented", response.data)

    def test_dual_partial_failure_is_visible_without_fallback(self):
        outputs = [
            self._natlas_result("Yoruba output"),
            ProviderUnavailableError("technical failure"),
        ]
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas", side_effect=outputs), \
             patch.object(application, "run_whisper") as whisper, \
             patch.object(application.os.path, "exists", return_value=False):
            response = self._post_audio(provider="dual_natlas", language="dual")
        whisper.assert_not_called()
        self.assertIn(b"model could not process", response.data)
        self.assertIn(b"One N-ATLAS model failed", response.data)

    def test_dual_over_30_seconds_stops_before_second_model(self):
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas", side_effect=NAtlasAudioTooLongError("31")) as natlas, \
             patch.object(application.os.path, "exists", return_value=False):
            response = self._post_audio(provider="dual_natlas", language="dual")
        self.assertEqual(natlas.call_count, 1)
        self.assertIn(b"up to 30 seconds", response.data)

    def _post_audio(self, *, provider="natlas", language="yo", model_size="small"):
        return self.client.post("/", data={
            "provider": provider,
            "language": language,
            "model_size": model_size,
            "audio": (wav_bytes(), "note.wav"),
        })

    @staticmethod
    def _natlas_result(transcript="Abeg deliver two phones to Mokola"):
        return ASRResult(
            engine="natlas",
            model="NCAIR1/Yoruba-ASR",
            transcript=transcript,
            detected_language="yo",
            audio_seconds=2.0,
            metadata={
                "confidence": None,
                "translation_performed": False,
                "language_provenance": "explicit_user_or_caller_selection",
            },
        )

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
            response = self._post_audio(provider="whisper", language="auto")
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
            response = self._post_audio(provider="whisper", language="auto")
        self.assertIn(b"Low confidence", response.data)

    def test_natlas_yoruba_success_and_explicit_provenance(self):
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas", return_value=self._natlas_result()) as natlas, \
             patch.object(application, "run_whisper", return_value=("Please deliver two phones", "en", 80, 80)), \
             patch.object(application.os.path, "exists", return_value=False):
            response = self._post_audio(language="yo")
        natlas.assert_called_once_with("processed.wav", "yo")
        self.assertIn(b"NCAIR1/Yoruba-ASR", response.data)
        self.assertIn(b"Explicit user selection", response.data)

    def test_natlas_nigerian_english_does_not_run_translation(self):
        asr = ASRResult(
            "natlas", "NCAIR1/NigerianAccentedEnglish", "I need two phones",
            "en-NG", metadata={"confidence": None, "translation_performed": False},
        )
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas", return_value=asr) as natlas, \
             patch.object(application, "run_whisper") as whisper, \
             patch.object(application.os.path, "exists", return_value=False):
            response = self._post_audio(language="en-NG")
        natlas.assert_called_once_with("processed.wav", "en-NG")
        whisper.assert_not_called()
        self.assertIn(b"NCAIR1/NigerianAccentedEnglish", response.data)
        self.assertIn(b"Not generated", response.data)

    def test_raw_natlas_transcript_is_preserved_separately_from_translation(self):
        raw = "Aise ayipada ọrọ olupese"
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas", return_value=self._natlas_result(raw)), \
             patch.object(application, "run_whisper", return_value=("English meaning differs", "en", 80, 80)), \
             patch.object(application.os.path, "exists", return_value=False):
            response = self._post_audio()
        self.assertIn(raw.encode(), response.data)
        self.assertIn(b"English meaning differs", response.data)
        self.assertIn(b"Original provider transcript", response.data)

    def test_natlas_translation_is_attributed_to_local_whisper(self):
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas", return_value=self._natlas_result()), \
             patch.object(application, "run_whisper", return_value=("English meaning", "en", 80, 80)), \
             patch.object(application.os.path, "exists", return_value=False):
            response = self._post_audio()
        self.assertIn(b"Local Whisper translation", response.data)
        self.assertNotIn(b"N-ATLAS translation", response.data)

    def test_user_correction_provenance_does_not_overwrite_raw_text(self):
        response = self.client.post("/analyze-action", json={
            "raw_transcript": "raw provider text",
            "transcript": "corrected customer request",
            "raw_english": "raw meaning",
            "english": "corrected meaning",
        })
        provenance = response.get_json()["correction_provenance"]
        self.assertEqual(provenance["raw_provider_transcript_preserved"], "raw provider text")
        self.assertTrue(provenance["transcript_user_corrected"])
        self.assertTrue(provenance["english_user_corrected"])

    def test_natlas_failure_has_no_automatic_whisper_fallback(self):
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas", side_effect=ProviderUnavailableError("failed")), \
             patch.object(application, "run_whisper") as whisper, \
             patch.object(application.os.path, "exists", return_value=False):
            response = self._post_audio()
        whisper.assert_not_called()
        self.assertIn(b"No fallback was performed", response.data)
        self.assertIn(b"Process explicitly with local Whisper", response.data)

    def test_explicit_subsequent_whisper_run_is_separate(self):
        outputs = [
            ("Whisper raw transcript", "en", 90, 90),
            ("Whisper English meaning", "en", 88, 90),
        ]
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas") as natlas, \
             patch.object(application, "run_whisper", side_effect=outputs) as whisper, \
             patch.object(application.os.path, "exists", return_value=False):
            response = self._post_audio(provider="whisper", language="auto")
        natlas.assert_not_called()
        self.assertEqual(whisper.call_count, 2)
        self.assertIn(b"Local Whisper", response.data)

    def test_natlas_over_30_seconds_is_rejected_without_whisper(self):
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas", side_effect=NAtlasAudioTooLongError("31 seconds")), \
             patch.object(application, "run_whisper") as whisper, \
             patch.object(application.os.path, "exists", return_value=False):
            response = self._post_audio()
        whisper.assert_not_called()
        self.assertIn(b"up to 30 seconds", response.data)
        self.assertIn(b"explicitly choose local Whisper", response.data)

    def test_unsupported_natlas_language_is_rejected_before_processing(self):
        with patch.object(application, "preprocess_audio") as preprocess, \
             patch.object(application, "run_natlas") as natlas:
            response = self._post_audio(language="pcm")
        preprocess.assert_not_called()
        natlas.assert_not_called()
        self.assertIn(b"not supported by the selected provider", response.data)

    def test_unknown_provider_is_rejected_without_implicit_switching(self):
        with patch.object(application, "preprocess_audio") as preprocess, \
             patch.object(application, "run_natlas") as natlas, \
             patch.object(application, "run_whisper") as whisper:
            response = self._post_audio(provider="unknown", language="yo")
        preprocess.assert_not_called()
        natlas.assert_not_called()
        whisper.assert_not_called()
        self.assertIn(b"No provider was selected or run automatically", response.data)

    def test_natlas_confidence_remains_unavailable(self):
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas", return_value=self._natlas_result()), \
             patch.object(application, "run_whisper", return_value=("English", "en", 80, 80)), \
             patch.object(application.os.path, "exists", return_value=False):
            response = self._post_audio()
        self.assertIn(b"Provider confidence</strong>Not provided", response.data)
        self.assertNotIn(b"Provider confidence</strong>0%", response.data)

    def test_natlas_preserves_never_guess_confirmation(self):
        asr = self._natlas_result("I have paid 15000 or 50000 naira")
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas", return_value=asr), \
             patch.object(application, "run_whisper", return_value=("I have paid 15000 or 50000 naira", "en", 80, 80)), \
             patch.object(application.os.path, "exists", return_value=False):
            response = self._post_audio()
        self.assertIn(b"ACTION PAUSED", response.data)
        self.assertIn(b"REQUIRES CONFIRMATION", response.data)

    def test_provider_switch_does_not_contaminate_new_output(self):
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_natlas", return_value=self._natlas_result("NATLAS UNIQUE RAW")), \
             patch.object(application, "run_whisper", return_value=("First meaning", "en", 80, 80)), \
             patch.object(application.os.path, "exists", return_value=False):
            first = self._post_audio()
        self.assertIn(b"NATLAS UNIQUE RAW", first.data)
        outputs = [("WHISPER NEW RAW", "en", 90, 90), ("Second meaning", "en", 90, 90)]
        with patch.object(application, "preprocess_audio", return_value="processed.wav"), \
             patch.object(application, "run_whisper", side_effect=outputs), \
             patch.object(application.os.path, "exists", return_value=False):
            second = self._post_audio(provider="whisper", language="auto")
        self.assertIn(b"WHISPER NEW RAW", second.data)
        self.assertNotIn(b"NATLAS UNIQUE RAW", second.data)


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
