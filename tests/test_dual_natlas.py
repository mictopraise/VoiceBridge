import unittest
from unittest.mock import patch

import app as application
from dual_natlas import compare_transcripts
from speech_engines.base import ASRResult, ProviderUnavailableError


def result(model, transcript, language):
    return ASRResult(
        engine="natlas", model=model, transcript=transcript,
        detected_language=language, metadata={"confidence": None},
    )


class DisagreementRulesTests(unittest.TestCase):
    def test_high_risk_quantity_and_location_disagreement(self):
        comparison = compare_transcripts(
            "deliver two phones to Mokola tomorrow",
            "deliver five phones to Ibadan tomorrow",
        )
        self.assertTrue(comparison["material_disagreement"])
        self.assertIn("numbers_or_quantities", comparison["categories"])
        self.assertIn("locations_or_addresses", comparison["categories"])
        self.assertIsNone(comparison["confidence"])
        self.assertIsNone(comparison["correct_model"])

    def test_payment_negation_is_material(self):
        comparison = compare_transcripts("I have paid", "I have not paid")
        self.assertIn("negations", comparison["categories"])
        self.assertTrue(comparison["review_required"])

    def test_agreement_is_not_called_proof(self):
        comparison = compare_transcripts("deliver two phones", "deliver two phones")
        self.assertFalse(comparison["material_disagreement"])
        self.assertIn("not proof", comparison["notice"].lower())


class DualExecutionTests(unittest.TestCase):
    def test_execution_order_is_yoruba_then_nigerian_english(self):
        calls = []
        def fake_run(path, language):
            calls.append(language)
            model = "NCAIR1/Yoruba-ASR" if language == "yo" else "NCAIR1/NigerianAccentedEnglish"
            return result(model, f"output {language}", language)
        with patch.object(application, "run_natlas", side_effect=fake_run):
            outputs, comparison = application.run_dual_natlas("audio.wav")
        self.assertEqual(calls, ["yo", "en-NG"])
        self.assertEqual(len(outputs), 2)
        self.assertTrue(comparison["review_required"])

    def test_one_failure_preserves_success_and_requires_review(self):
        outcomes = [
            ProviderUnavailableError("unavailable"),
            result("NCAIR1/NigerianAccentedEnglish", "send two phones", "en-NG"),
        ]
        with patch.object(application, "run_natlas", side_effect=outcomes):
            outputs, comparison = application.run_dual_natlas("audio.wav")
        self.assertEqual(outputs[0]["status"], "failed")
        self.assertEqual(outputs[1]["status"], "completed")
        self.assertTrue(comparison["review_required"])
        self.assertIn("technical_model_failure", comparison["categories"])

    def test_two_failures_are_not_silently_fallbacked(self):
        with patch.object(
            application, "run_natlas", side_effect=ProviderUnavailableError("failed")
        ), patch.object(application, "run_whisper") as whisper:
            with self.assertRaises(ProviderUnavailableError):
                application.run_dual_natlas("audio.wav")
        whisper.assert_not_called()

