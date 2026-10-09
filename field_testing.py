"""Local, privacy-conscious storage for NAIC field-test interactions."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import io
import json
import os
import re
import tempfile
from threading import Lock


FIELDS = (
    "interaction_id",
    "date_time",
    "audio_code",
    "audio_filename",
    "recording_key",
    "participant_code",
    "consent_confirmed",
    "language_or_language_mix",
    "environment_noise_level",
    "use_case",
    "provider",
    "model",
    "selected_language",
    "selected_language_source",
    "processing_status",
    "processing_mode",
    "material_disagreement",
    "asr_outcome",
    "semantic_meaning_correct",
    "critical_fields_correct",
    "never_guess_triggered",
    "correction_required",
    "action_card_useful",
    "task_completion",
    "human_reference_meaning",
    "verified_critical_information",
    "short_user_feedback",
    "tester_notes",
    "evaluation_count",
)

CHOICES = {
    "language_or_language_mix": {
        "Nigerian-accented English",
        "Yoruba",
        "Yoruba-English",
        "Pidgin-English",
        "Other",
    },
    "environment_noise_level": {"quiet", "moderate", "noisy"},
    "asr_outcome": {"pass", "partial", "fail"},
    "semantic_meaning_correct": {"yes", "partial", "no"},
    "critical_fields_correct": {"yes", "partial", "no", "n/a"},
    "correction_required": {"none", "minor", "major"},
    "action_card_useful": {"yes", "partial", "no"},
    "task_completion": {"completed", "not_completed"},
}

SUMMARY_FIELDS = (
    "language_or_language_mix",
    "provider",
    "asr_outcome",
    "semantic_meaning_correct",
    "correction_required",
    "task_completion",
    "never_guess_triggered",
)

_write_lock = Lock()
_audio_code_pattern = re.compile(r"^(VB-\d{3,6})(?:[_\-.]|$)", re.IGNORECASE)


class FieldTestValidationError(ValueError):
    """Raised when an interaction would violate the local logging schema."""


def _clean(value, max_length=500):
    return " ".join(str(value or "").strip().split())[:max_length]


def _boolean(value):
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"true", "yes", "1", "on"}:
        return True
    if normalized in {"false", "no", "0", "off", ""}:
        return False
    raise FieldTestValidationError("Invalid boolean field value.")


def safe_audio_identity(filename, audio_sha256=None):
    """Return a safe basename, optional VB code, and stable local recording key."""
    basename = Path(str(filename or "").replace("\\", "/")).name
    basename = _clean(basename, 240)
    match = _audio_code_pattern.match(basename)
    audio_code = match.group(1).upper() if match else ""
    digest = str(audio_sha256 or "").lower()
    if digest and not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise FieldTestValidationError("Invalid audio SHA-256 value.")
    recording_key = f"code:{audio_code}" if audio_code else (
        f"sha256:{digest}" if digest else (f"filename:{basename.casefold()}" if basename else "")
    )
    return {
        "audio_filename": basename,
        "audio_code": audio_code,
        "recording_key": recording_key,
    }


def audio_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_interaction(payload):
    """Return a normalized interaction without collecting direct identifiers."""
    record = {
        "audio_filename": _clean(payload.get("audio_filename"), 240),
        "audio_code": _clean(payload.get("audio_code"), 20).upper(),
        "recording_key": _clean(payload.get("recording_key"), 280),
        "participant_code": _clean(payload.get("participant_code"), 40),
        "consent_confirmed": _boolean(payload.get("consent_confirmed")),
        "language_or_language_mix": _clean(payload.get("language_or_language_mix"), 80),
        "environment_noise_level": _clean(payload.get("environment_noise_level"), 20),
        "use_case": _clean(payload.get("use_case"), 120),
        "provider": _clean(payload.get("provider"), 100),
        "model": _clean(payload.get("model"), 180),
        "selected_language": _clean(payload.get("selected_language"), 80),
        "selected_language_source": _clean(payload.get("selected_language_source"), 80),
        "processing_status": _clean(payload.get("processing_status") or "completed", 30),
        "processing_mode": _clean(payload.get("processing_mode") or "single_model", 40),
        "material_disagreement": _boolean(payload.get("material_disagreement")),
        "disagreement_categories": payload.get("disagreement_categories") or {},
        "model_outputs": payload.get("model_outputs") or [],
        "starting_model": _clean(payload.get("starting_model"), 180),
        "asr_outcome": _clean(payload.get("asr_outcome"), 20),
        "semantic_meaning_correct": _clean(payload.get("semantic_meaning_correct"), 20),
        "critical_fields_correct": _clean(payload.get("critical_fields_correct"), 20),
        "never_guess_triggered": _boolean(payload.get("never_guess_triggered")),
        "correction_required": _clean(payload.get("correction_required"), 20),
        "action_card_useful": _clean(payload.get("action_card_useful"), 20),
        "task_completion": _clean(payload.get("task_completion"), 30),
        "human_reference_meaning": _clean(payload.get("human_reference_meaning"), 1500),
        "verified_critical_information": _clean(
            payload.get("verified_critical_information"), 1500
        ),
        "short_user_feedback": _clean(payload.get("short_user_feedback"), 500),
        "tester_notes": _clean(payload.get("tester_notes"), 1000),
        "store_transcripts": _boolean(payload.get("store_transcripts")),
        "raw_provider_transcript": _clean(payload.get("raw_provider_transcript"), 5000),
        "working_transcript": _clean(payload.get("working_transcript"), 5000),
        "english_meaning": _clean(payload.get("english_meaning"), 5000),
        "evaluation_mode": _clean(payload.get("evaluation_mode") or "new", 20),
    }
    if not record["recording_key"] and (
        record["audio_filename"] or record["audio_code"]
    ):
        derived = safe_audio_identity(record["audio_filename"])
        if not record["audio_code"]:
            record["audio_code"] = derived["audio_code"]
        record["recording_key"] = (
            f"code:{record['audio_code']}" if record["audio_code"]
            else derived["recording_key"]
        )
    required = (
        "participant_code", "language_or_language_mix", "environment_noise_level",
        "use_case", "provider", "model", "asr_outcome",
        "semantic_meaning_correct", "critical_fields_correct",
        "correction_required", "action_card_useful", "task_completion",
    )
    missing = [name for name in required if not record[name]]
    if missing:
        raise FieldTestValidationError(
            "Complete all required fields: " + ", ".join(missing)
        )
    if not record["consent_confirmed"]:
        raise FieldTestValidationError("Confirmed consent is required before logging.")
    if record["audio_code"] and not re.fullmatch(r"VB-\d{3,6}", record["audio_code"]):
        raise FieldTestValidationError("Audio code must use the VB-001 format.")
    if record["evaluation_mode"] not in {"new", "comparison", "retest"}:
        raise FieldTestValidationError("Invalid evaluation mode.")
    for name, allowed in CHOICES.items():
        if record[name] not in allowed:
            raise FieldTestValidationError(f"Invalid value for {name}.")
    if not record["store_transcripts"]:
        record["raw_provider_transcript"] = ""
        record["working_transcript"] = ""
        record["english_meaning"] = ""
        for item in record["model_outputs"]:
            if isinstance(item, dict):
                item.pop("transcript", None)
    if not isinstance(record["disagreement_categories"], dict):
        raise FieldTestValidationError("Invalid disagreement metadata.")
    if not isinstance(record["model_outputs"], list):
        raise FieldTestValidationError("Invalid model-evaluation metadata.")
    return record


def load_interactions(path):
    path = Path(path)
    if not path.exists():
        return []
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FieldTestValidationError("The local field-test log is unreadable.") from exc
    if not isinstance(content, list):
        raise FieldTestValidationError("The local field-test log has an invalid format.")
    return content


def _next_id(records):
    numbers = []
    for record in records:
        identifier = str(record.get("interaction_id", ""))
        if identifier.startswith("VB-") and identifier[3:].isdigit():
            numbers.append(int(identifier[3:]))
    return f"VB-{max(numbers, default=0) + 1:03d}"


def _atomic_write(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _next_evaluation_id(record):
    evaluations = record.get("evaluations") or []
    return f"EVAL-{len(evaluations) + 1:03d}"


def _evaluation(record, now):
    excluded = {
        "participant_code", "consent_confirmed", "language_or_language_mix",
        "environment_noise_level", "audio_filename", "audio_code", "recording_key",
        "evaluation_mode",
    }
    return {
        "evaluation_id": "EVAL-001",
        "evaluated_at": now.isoformat(),
        "mode": record["evaluation_mode"],
        **{key: value for key, value in record.items() if key not in excluded},
    }


def _dual_evaluations(record, now):
    """Represent one genuine interaction with two provider-model evaluations."""
    outputs = record.get("model_outputs") or []
    if record.get("processing_mode") != "dual_natlas_review" or not outputs:
        return [_evaluation(record, now)]
    evaluations = []
    for position, output in enumerate(outputs, start=1):
        evaluation = _evaluation(record, now)
        evaluation.update({
            "evaluation_id": f"EVAL-{position:03d}",
            "provider": "NCAIR N-ATLAS",
            "model": output.get("model", ""),
            "selected_language": output.get("language", ""),
            "processing_status": output.get("status", "unknown"),
            "processing_mode": "dual_natlas_review",
            "material_disagreement": record.get("material_disagreement", False),
            "starting_transcript_selected": output.get("model") == record.get("starting_model"),
        })
        if record.get("store_transcripts"):
            evaluation["raw_provider_transcript"] = output.get("transcript", "")
        evaluations.append(evaluation)
    return evaluations


def find_interaction(records, recording_key):
    if not recording_key:
        return None
    return next(
        (record for record in records if record.get("recording_key") == recording_key),
        None,
    )


def _ensure_evaluations(record):
    if record.get("evaluations"):
        return record["evaluations"]
    legacy = {
        "evaluation_id": "EVAL-001",
        "evaluated_at": record.get("date_time", ""),
        "mode": "new",
    }
    for field in (
        "use_case", "provider", "model", "selected_language",
        "selected_language_source", "processing_status", "asr_outcome",
        "semantic_meaning_correct", "critical_fields_correct",
        "never_guess_triggered", "correction_required", "action_card_useful",
        "task_completion", "human_reference_meaning",
        "verified_critical_information", "short_user_feedback", "tester_notes",
    ):
        legacy[field] = record.get(field, "")
    record["evaluations"] = [legacy]
    record["evaluation_count"] = 1
    return record["evaluations"]


def save_interaction(path, payload, now=None):
    normalized = validate_interaction(payload)
    timestamp = now or datetime.now(timezone.utc)
    with _write_lock:
        records = load_interactions(path)
        existing = find_interaction(records, normalized["recording_key"])
        mode = normalized["evaluation_mode"]
        if existing:
            if mode == "new":
                raise FieldTestValidationError(
                    f"This recording is already saved as {existing['interaction_id']}. "
                    "Choose provider comparison or intentional retest instead."
                )
            evaluations = _ensure_evaluations(existing)
            if mode == "comparison" and any(
                item.get("provider") == normalized["provider"]
                and item.get("model") == normalized["model"]
                for item in evaluations
            ):
                raise FieldTestValidationError(
                    "That provider/model is already evaluated for this recording. "
                    "Choose intentional retest to preserve another run."
                )
            evaluation = _evaluation(normalized, timestamp)
            evaluation["evaluation_id"] = _next_evaluation_id(existing)
            evaluations.append(evaluation)
            existing["evaluation_count"] = len(evaluations)
            existing["last_evaluated_at"] = timestamp.isoformat()
            outcome = {"record": existing, "evaluation": evaluation, "created": False}
        else:
            if mode != "new":
                raise FieldTestValidationError(
                    "No saved interaction matches this recording; save it as a new interaction first."
                )
            evaluations = _dual_evaluations(normalized, timestamp)
            evaluation = evaluations[0]
            record = {
                "interaction_id": _next_id(records),
                "date_time": timestamp.isoformat(),
                **{key: value for key, value in normalized.items()
                   if key not in {"evaluation_mode", "store_transcripts"}},
                "evaluation_count": len(evaluations),
                "evaluations": evaluations,
            }
            records.append(record)
            outcome = {"record": record, "evaluation": evaluation, "created": True}
        _atomic_write(path, records)
    return outcome


def append_interaction(path, payload, now=None):
    mutable = dict(payload)
    mutable.setdefault("evaluation_mode", "new")
    return save_interaction(path, mutable, now)["record"]


def summarize(records, processed_records=None):
    recordings = {record.get("recording_key") for record in records if record.get("recording_key")}
    summary = {
        "total_interactions": len(records),
        "saved_genuine_interactions": len(records),
        "recordings_reviewed": len(recordings) or len(records),
        "processed_recordings": len(processed_records or []),
        "total_evaluations": sum(int(record.get("evaluation_count", 1)) for record in records),
        "target": 50,
        "counts": {},
    }
    for field in SUMMARY_FIELDS:
        counter = Counter(str(record.get(field, "unknown")).lower() for record in records)
        summary["counts"][field] = dict(sorted(counter.items()))
    summary["target_mix"] = {
        "Nigerian-accented English": 20,
        "Yoruba": 15,
        "Yoruba-English": 10,
        "Pidgin-English": 5,
    }
    summary["privacy"] = (
        "Aggregate counts only; excludes participant codes, feedback, notes, audio, "
        "phone numbers and addresses."
    )
    return summary


def export_json(records):
    return json.dumps(records, ensure_ascii=False, indent=2) + "\n"


def export_csv(records):
    def csv_safe(value):
        text = str(value) if value is not None else ""
        return "'" + text if text.startswith(("=", "+", "-", "@")) else text

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(
        {field: csv_safe(record.get(field, "")) for field in FIELDS}
        for record in records
    )
    return output.getvalue()


def sanitized_summary_json(records, processed_records=None):
    return json.dumps(
        summarize(records, processed_records), ensure_ascii=False, indent=2
    ) + "\n"


def load_processing_index(path):
    return load_interactions(path)


def register_processed(path, identity, provider, model, now=None):
    timestamp = (now or datetime.now(timezone.utc)).isoformat()
    recording_key = identity.get("recording_key")
    if not recording_key:
        return None
    with _write_lock:
        entries = load_processing_index(path)
        entry = next(
            (item for item in entries if item.get("recording_key") == recording_key),
            None,
        )
        provider_identity = {"provider": _clean(provider, 100), "model": _clean(model, 180)}
        if entry is None:
            entry = {
                **identity,
                "first_processed_at": timestamp,
                "last_processed_at": timestamp,
                "processing_run_count": 1,
                "providers": [provider_identity],
            }
            entries.append(entry)
        else:
            entry["last_processed_at"] = timestamp
            entry["processing_run_count"] = int(entry.get("processing_run_count", 0)) + 1
            if provider_identity not in entry.setdefault("providers", []):
                entry["providers"].append(provider_identity)
        _atomic_write(path, entries)
    return entry


def recording_manifest_csv(processed_records, interactions):
    output = io.StringIO(newline="")
    fields = (
        "audio_code", "audio_filename", "recording_key", "processed_run_count",
        "providers", "reviewed", "interaction_id", "evaluation_count",
    )
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for item in processed_records:
        interaction = find_interaction(interactions, item.get("recording_key"))
        writer.writerow({
            "audio_code": item.get("audio_code", ""),
            "audio_filename": item.get("audio_filename", ""),
            "recording_key": item.get("recording_key", ""),
            "processed_run_count": item.get("processing_run_count", 0),
            "providers": "; ".join(
                f"{entry.get('provider', '')} | {entry.get('model', '')}"
                for entry in item.get("providers", [])
            ),
            "reviewed": "yes" if interaction else "no",
            "interaction_id": interaction.get("interaction_id", "") if interaction else "",
            "evaluation_count": interaction.get("evaluation_count", 0) if interaction else 0,
        })
    return output.getvalue()
