import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import app as application
from field_testing import (
    FieldTestValidationError,
    append_interaction,
    export_csv,
    load_interactions,
    sanitized_summary_json,
    summarize,
)


def valid_payload(**overrides):
    payload = {
        "participant_code": "P-001",
        "consent_confirmed": "on",
        "language_or_language_mix": "Yoruba-English",
        "environment_noise_level": "moderate",
        "use_case": "delivery request",
        "provider": "NCAIR N-ATLAS",
        "model": "NCAIR1/Yoruba-ASR",
        "asr_outcome": "partial",
        "semantic_meaning_correct": "yes",
        "critical_fields_correct": "partial",
        "never_guess_triggered": "on",
        "correction_required": "minor",
        "action_card_useful": "yes",
        "task_completion": "completed",
        "short_user_feedback": "The action was understandable.",
        "tester_notes": "Location required correction.",
    }
    payload.update(overrides)
    return payload


class FieldTestingStorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "private" / "interactions.json"

    def tearDown(self):
        self.directory.cleanup()

    def test_sequential_ids_and_atomic_local_storage(self):
        first = append_interaction(
            self.path, valid_payload(), datetime(2026, 10, 2, tzinfo=timezone.utc)
        )
        second = append_interaction(self.path, valid_payload(participant_code="P-002"))
        self.assertEqual(first["interaction_id"], "VB-001")
        self.assertEqual(second["interaction_id"], "VB-002")
        self.assertEqual(len(load_interactions(self.path)), 2)

    def test_consent_is_required(self):
        with self.assertRaisesRegex(FieldTestValidationError, "consent"):
            append_interaction(self.path, valid_payload(consent_confirmed=""))

    def test_invalid_choice_is_rejected(self):
        with self.assertRaisesRegex(FieldTestValidationError, "asr_outcome"):
            append_interaction(self.path, valid_payload(asr_outcome="excellent"))

    def test_summary_counts_required_dimensions(self):
        append_interaction(self.path, valid_payload())
        summary = summarize(load_interactions(self.path))
        self.assertEqual(summary["total_interactions"], 1)
        self.assertEqual(summary["counts"]["provider"]["ncair n-atlas"], 1)
        self.assertEqual(summary["counts"]["never_guess_triggered"]["true"], 1)

    def test_sanitized_summary_excludes_private_and_free_text_fields(self):
        append_interaction(self.path, valid_payload())
        exported = sanitized_summary_json(load_interactions(self.path))
        self.assertNotIn("P-001", exported)
        self.assertNotIn("Location required correction", exported)
        self.assertNotIn("The action was understandable", exported)
        self.assertNotIn("participant_code", exported)
        self.assertIn('"total_interactions": 1', exported)

    def test_private_csv_contains_all_requested_columns(self):
        append_interaction(self.path, valid_payload())
        exported = export_csv(load_interactions(self.path))
        self.assertIn("interaction_id,date_time,participant_code", exported)
        self.assertIn("VB-001", exported)
        self.assertIn("tester_notes", exported)

    def test_csv_export_neutralizes_spreadsheet_formulas(self):
        append_interaction(
            self.path,
            valid_payload(short_user_feedback="=HYPERLINK malicious formula"),
        )
        exported = export_csv(load_interactions(self.path))
        self.assertIn("'=HYPERLINK malicious formula", exported)


class FieldTestingRouteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "interactions.json"
        application.app.config.update(
            TESTING=True,
            FIELD_TEST_LOG_PATH=str(self.path),
        )
        self.client = application.app.test_client()

    def tearDown(self):
        self.directory.cleanup()

    def test_field_testing_page_is_available(self):
        response = self.client.get("/field-testing")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"VoiceBridge Field Testing", response.data)
        self.assertIn(b"Do not enter names", response.data)

    def test_form_saves_and_redirects_to_prevent_duplicate_refresh(self):
        response = self.client.post("/field-testing", data=valid_payload())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/field-testing?saved=VB-001"))
        self.client.get(response.location)
        self.assertEqual(len(load_interactions(self.path)), 1)

    def test_exports_have_expected_content_and_disposition(self):
        append_interaction(self.path, valid_payload())
        csv_response = self.client.get("/field-testing/export.csv")
        json_response = self.client.get("/field-testing/export.json")
        summary_response = self.client.get("/field-testing/sanitized-summary.json")
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("attachment", csv_response.headers["Content-Disposition"])
        self.assertEqual(json.loads(json_response.data)[0]["interaction_id"], "VB-001")
        summary = json.loads(summary_response.data)
        self.assertEqual(summary["total_interactions"], 1)
        self.assertNotIn("participant_code", summary)

    def test_failed_consent_does_not_write_record(self):
        response = self.client.post(
            "/field-testing", data=valid_payload(consent_confirmed="")
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Confirmed consent is required", response.data)
        self.assertFalse(self.path.exists())
