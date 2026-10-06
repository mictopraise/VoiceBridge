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
    recording_manifest_csv,
    register_processed,
    load_interactions,
    save_interaction,
    safe_audio_identity,
    sanitized_summary_json,
    summarize,
)
from inference_drafts import InferenceDraftStore


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
        self.assertIn("interaction_id,date_time,audio_code,audio_filename", exported)
        self.assertIn("VB-001", exported)
        self.assertIn("tester_notes", exported)

    def test_csv_export_neutralizes_spreadsheet_formulas(self):
        append_interaction(
            self.path,
            valid_payload(short_user_feedback="=HYPERLINK malicious formula"),
        )
        exported = export_csv(load_interactions(self.path))
        self.assertIn("'=HYPERLINK malicious formula", exported)

    def test_audio_code_is_safely_extracted_from_portable_filename(self):
        identity = safe_audio_identity(
            r"C:\private\VB-017_customer-note.ogg", "a" * 64
        )
        self.assertEqual(identity["audio_filename"], "VB-017_customer-note.ogg")
        self.assertEqual(identity["audio_code"], "VB-017")
        self.assertEqual(identity["recording_key"], "code:VB-017")
        invalid = safe_audio_identity("customer_VB-017.ogg", "b" * 64)
        self.assertEqual(invalid["audio_code"], "")
        self.assertEqual(invalid["recording_key"], "sha256:" + "b" * 64)

    def test_duplicate_recording_is_blocked_but_comparison_is_auditable(self):
        identity = safe_audio_identity("VB-003_order.ogg", "c" * 64)
        first = save_interaction(self.path, valid_payload(**identity))
        self.assertTrue(first["created"])
        with self.assertRaisesRegex(FieldTestValidationError, "already saved"):
            save_interaction(self.path, valid_payload(**identity))
        comparison = save_interaction(self.path, valid_payload(
            **identity,
            provider="Local Whisper",
            model="large-v3",
            evaluation_mode="comparison",
        ))
        self.assertFalse(comparison["created"])
        records = load_interactions(self.path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["evaluation_count"], 2)
        self.assertEqual(records[0]["evaluations"][1]["mode"], "comparison")

    def test_same_model_requires_intentional_retest(self):
        identity = safe_audio_identity("VB-004_order.ogg", "d" * 64)
        save_interaction(self.path, valid_payload(**identity))
        with self.assertRaisesRegex(FieldTestValidationError, "intentional retest"):
            save_interaction(self.path, valid_payload(
                **identity, evaluation_mode="comparison"
            ))
        outcome = save_interaction(self.path, valid_payload(
            **identity, evaluation_mode="retest"
        ))
        self.assertFalse(outcome["created"])
        self.assertEqual(outcome["record"]["evaluation_count"], 2)

    def test_transcripts_are_not_persisted_without_explicit_opt_in(self):
        identity = safe_audio_identity("VB-005_order.ogg", "e" * 64)
        outcome = save_interaction(self.path, valid_payload(
            **identity,
            raw_provider_transcript="private raw words",
            working_transcript="edited words",
            english_meaning="private meaning",
        ))
        encoded = json.dumps(outcome["record"])
        self.assertNotIn("private raw words", encoded)
        self.assertNotIn("edited words", encoded)
        self.assertNotIn("private meaning", encoded)

    def test_explicit_transcript_opt_in_is_honoured_in_private_json(self):
        identity = safe_audio_identity("VB-006_order.ogg", "f" * 64)
        outcome = save_interaction(self.path, valid_payload(
            **identity,
            store_transcripts="on",
            raw_provider_transcript="consented raw words",
            working_transcript="consented edited words",
        ))
        self.assertEqual(
            outcome["record"]["raw_provider_transcript"], "consented raw words"
        )
        public_summary = sanitized_summary_json([outcome["record"]])
        self.assertNotIn("consented raw words", public_summary)
        self.assertNotIn("consented edited words", public_summary)

    def test_manifest_keeps_recording_and_interaction_ids_distinct(self):
        identity = safe_audio_identity("VB-007_order.ogg", "1" * 64)
        record = save_interaction(self.path, valid_payload(**identity))["record"]
        manifest = recording_manifest_csv([{
            **identity,
            "processing_run_count": 2,
            "providers": [{"provider": "NCAIR N-ATLAS", "model": "NCAIR1/Yoruba-ASR"}],
        }], [record])
        self.assertIn("VB-007", manifest)
        self.assertIn("VB-001", manifest)
        self.assertIn("yes", manifest)

    def test_comparison_migrates_legacy_record_without_losing_first_evaluation(self):
        identity = safe_audio_identity("VB-008_order.ogg", "2" * 64)
        legacy = {"interaction_id": "VB-001", "date_time": "2026-10-02T00:00:00+00:00", **valid_payload(**identity)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([legacy]), encoding="utf-8")
        outcome = save_interaction(self.path, valid_payload(
            **identity,
            provider="Local Whisper",
            model="large-v3",
            evaluation_mode="comparison",
        ))
        self.assertEqual(outcome["record"]["evaluation_count"], 2)
        self.assertEqual(outcome["record"]["evaluations"][0]["provider"], "NCAIR N-ATLAS")

    def test_processing_index_counts_recordings_separately_from_runs(self):
        index_path = Path(self.directory.name) / "processed.json"
        identity = safe_audio_identity("VB-009_order.ogg", "3" * 64)
        register_processed(index_path, identity, "NCAIR N-ATLAS", "NCAIR1/Yoruba-ASR")
        register_processed(index_path, identity, "Local Whisper", "large-v3")
        entries = load_interactions(index_path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["processing_run_count"], 2)
        self.assertEqual(len(entries[0]["providers"]), 2)


class InferenceDraftStoreTests(unittest.TestCase):
    def test_draft_expires_and_can_be_consumed_once(self):
        clock = [10.0]
        store = InferenceDraftStore(ttl_seconds=30, clock=lambda: clock[0])
        token = store.create({"raw": "private transcript"})
        self.assertEqual(store.get(token)["raw"], "private transcript")
        self.assertEqual(store.consume(token)["raw"], "private transcript")
        self.assertIsNone(store.get(token))
        expired = store.create({"raw": "second"})
        clock[0] = 41.0
        self.assertIsNone(store.get(expired))


class FieldTestingRouteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "interactions.json"
        self.processing_path = Path(self.directory.name) / "processed.json"
        application.app.config.update(
            TESTING=True,
            FIELD_TEST_LOG_PATH=str(self.path),
            FIELD_TEST_PROCESSING_INDEX_PATH=str(self.processing_path),
        )
        application._inference_drafts.clear()
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

    @staticmethod
    def draft_payload(**overrides):
        payload = {
            "audio_filename": "VB-011_delivery.ogg",
            "audio_code": "VB-011",
            "recording_key": "code:VB-011",
            "provider": "NCAIR N-ATLAS",
            "model": "NCAIR1/Yoruba-ASR",
            "selected_language": "Yoruba",
            "selected_language_source": "Explicit user selection",
            "language_code": "yo",
            "confidence": None,
            "raw_provider_transcript": "raw immutable words",
            "working_transcript": "deliver two phones tomorrow",
            "english_meaning": "Deliver two phones tomorrow",
        }
        payload.update(overrides)
        return payload

    def _create_draft(self, **overrides):
        seed = self.draft_payload(**overrides)
        seed_token = application._inference_drafts.create(seed)
        response = self.client.post(
            "/field-testing/draft", json={
                "seed_token": seed_token,
                "working_transcript": seed["working_transcript"],
                "english_meaning": seed["english_meaning"],
            }
        )
        self.assertEqual(response.status_code, 200)
        return response.get_json()["review_url"]

    def test_inference_draft_prefills_system_fields_without_url_transcript(self):
        review_url = self._create_draft()
        self.assertNotIn("raw immutable words", review_url)
        response = self.client.get(review_url)
        self.assertIn(b"VB-011_delivery.ogg", response.data)
        self.assertIn(b"NCAIR1/Yoruba-ASR", response.data)
        self.assertIn(b"Explicit user selection", response.data)
        self.assertIn(b"raw immutable words", response.data)
        self.assertIn(b"Human review required", response.data)
        self.assertNotIn(b'<option value="pass" selected', response.data)
        self.assertNotIn(b'name="consent_confirmed" required checked', response.data)

    def test_missing_or_expired_draft_is_reported_without_crash(self):
        response = self.client.get("/field-testing?draft=missing-token")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"missing or expired", response.data)

    def test_missing_seed_and_incomplete_seed_are_rejected(self):
        missing = self.client.post("/field-testing/draft", json={})
        self.assertEqual(missing.status_code, 410)
        seed_token = application._inference_drafts.create({
            **self.draft_payload(), "raw_provider_transcript": ""
        })
        incomplete = self.client.post("/field-testing/draft", json={
            "seed_token": seed_token,
            "working_transcript": "working",
            "english_meaning": "meaning",
        })
        self.assertEqual(incomplete.status_code, 400)

    def test_repeated_log_click_cannot_reuse_same_seed(self):
        seed = self.draft_payload()
        seed_token = application._inference_drafts.create(seed)
        payload = {
            "seed_token": seed_token,
            "working_transcript": seed["working_transcript"],
            "english_meaning": seed["english_meaning"],
        }
        first = self.client.post("/field-testing/draft", json=payload)
        second = self.client.post("/field-testing/draft", json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 410)

    def test_integrated_save_uses_trusted_system_fields_and_consumes_draft(self):
        review_url = self._create_draft()
        token = review_url.split("draft=", 1)[1]
        form = valid_payload(
            draft_token=token,
            provider="forged provider",
            model="forged model",
            evaluation_mode="new",
        )
        response = self.client.post("/field-testing", data=form)
        self.assertEqual(response.status_code, 302)
        record = load_interactions(self.path)[0]
        self.assertEqual(record["provider"], "NCAIR N-ATLAS")
        self.assertEqual(record["model"], "NCAIR1/Yoruba-ASR")
        self.assertEqual(record["audio_code"], "VB-011")
        self.assertNotIn("raw immutable words", json.dumps(record))
        self.assertIsNone(application._inference_drafts.get(token))

    def test_repeated_recording_does_not_create_second_genuine_interaction(self):
        first_url = self._create_draft()
        first_token = first_url.split("draft=", 1)[1]
        self.client.post("/field-testing", data=valid_payload(
            draft_token=first_token, evaluation_mode="new"
        ))
        second_url = self._create_draft(
            provider="Local Whisper", model="large-v3"
        )
        second_token = second_url.split("draft=", 1)[1]
        blocked = self.client.post("/field-testing", data=valid_payload(
            draft_token=second_token, evaluation_mode="new"
        ))
        self.assertIn(b"already saved", blocked.data)
        comparison = self.client.post("/field-testing", data=valid_payload(
            draft_token=second_token,
            evaluation_mode="comparison",
            provider="Local Whisper",
            model="large-v3",
        ))
        self.assertEqual(comparison.status_code, 302)
        records = load_interactions(self.path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["evaluation_count"], 2)

    def test_recording_manifest_export_is_available(self):
        self.processing_path.write_text(json.dumps([{
            "audio_code": "VB-020",
            "audio_filename": "VB-020_note.ogg",
            "recording_key": "code:VB-020",
            "processing_run_count": 1,
            "providers": [],
        }]), encoding="utf-8")
        response = self.client.get("/field-testing/recording-manifest.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"VB-020", response.data)
