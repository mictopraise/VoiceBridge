"""Manifest loading and validation without invented metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = ("sample_id", "audio_path", "reference_transcript")


class ManifestError(ValueError):
    pass


def validate_sample(sample: dict[str, Any], line_number: int | None = None) -> dict[str, Any]:
    location = f" on line {line_number}" if line_number else ""
    if not isinstance(sample, dict):
        raise ManifestError(f"Manifest item{location} must be a JSON object.")
    for field in REQUIRED_FIELDS:
        if field not in sample or not isinstance(sample[field], str) or not sample[field].strip():
            raise ManifestError(f"Field '{field}'{location} must be a non-empty string.")
    if "languages" in sample and not (
        isinstance(sample["languages"], list)
        and all(isinstance(item, str) and item for item in sample["languages"])
    ):
        raise ManifestError(f"Field 'languages'{location} must be a list of language codes.")
    if "reference_entities" in sample and not isinstance(sample["reference_entities"], dict):
        raise ManifestError(f"Field 'reference_entities'{location} must be an object.")
    if "reference_needs_confirmation" in sample and not isinstance(sample["reference_needs_confirmation"], bool):
        raise ManifestError(f"Field 'reference_needs_confirmation'{location} must be boolean.")
    return sample


def load_manifest(path: str | Path) -> list[dict[str, Any]]:
    manifest_path = Path(path)
    samples = []
    seen = set()
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                sample = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ManifestError(f"Invalid JSON on line {line_number}: {exc.msg}") from exc
            validate_sample(sample, line_number)
            if sample["sample_id"] in seen:
                raise ManifestError(f"Duplicate sample_id on line {line_number}: {sample['sample_id']}")
            seen.add(sample["sample_id"])
            samples.append(sample)
    if not samples:
        raise ManifestError("Manifest contains no samples.")
    return samples
