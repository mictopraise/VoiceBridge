"""Local, privacy-conscious storage for NAIC field-test interactions."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import csv
import io
import json
import os
import tempfile
from threading import Lock


FIELDS = (
    "interaction_id",
    "date_time",
    "participant_code",
    "consent_confirmed",
    "language_or_language_mix",
    "environment_noise_level",
    "use_case",
    "provider",
    "model",
    "asr_outcome",
    "semantic_meaning_correct",
    "critical_fields_correct",
    "never_guess_triggered",
    "correction_required",
    "action_card_useful",
    "task_completion",
    "short_user_feedback",
    "tester_notes",
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


def validate_interaction(payload):
    """Return a normalized interaction without collecting direct identifiers."""
    record = {
        "participant_code": _clean(payload.get("participant_code"), 40),
        "consent_confirmed": _boolean(payload.get("consent_confirmed")),
        "language_or_language_mix": _clean(payload.get("language_or_language_mix"), 80),
        "environment_noise_level": _clean(payload.get("environment_noise_level"), 20),
        "use_case": _clean(payload.get("use_case"), 120),
        "provider": _clean(payload.get("provider"), 100),
        "model": _clean(payload.get("model"), 180),
        "asr_outcome": _clean(payload.get("asr_outcome"), 20),
        "semantic_meaning_correct": _clean(payload.get("semantic_meaning_correct"), 20),
        "critical_fields_correct": _clean(payload.get("critical_fields_correct"), 20),
        "never_guess_triggered": _boolean(payload.get("never_guess_triggered")),
        "correction_required": _clean(payload.get("correction_required"), 20),
        "action_card_useful": _clean(payload.get("action_card_useful"), 20),
        "task_completion": _clean(payload.get("task_completion"), 30),
        "short_user_feedback": _clean(payload.get("short_user_feedback"), 500),
        "tester_notes": _clean(payload.get("tester_notes"), 1000),
    }
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
    for name, allowed in CHOICES.items():
        if record[name] not in allowed:
            raise FieldTestValidationError(f"Invalid value for {name}.")
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


def append_interaction(path, payload, now=None):
    record = validate_interaction(payload)
    with _write_lock:
        records = load_interactions(path)
        record = {
            "interaction_id": _next_id(records),
            "date_time": (now or datetime.now(timezone.utc)).isoformat(),
            **record,
        }
        records.append(record)
        _atomic_write(path, records)
    return record


def summarize(records):
    summary = {"total_interactions": len(records), "counts": {}}
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


def sanitized_summary_json(records):
    return json.dumps(summarize(records), ensure_ascii=False, indent=2) + "\n"
