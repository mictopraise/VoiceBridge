"""VoiceBridge-owned downstream business and safety scoring."""

from __future__ import annotations

from typing import Any
from .metrics import normalize_text

CRITICAL_FIELDS = {"amount", "quantity", "location", "date", "time", "payment_status", "phone_or_reference"}


def _comparable(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, list):
        return sorted(_comparable(item) for item in value)
    return value


def evaluate_action(action: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    reference_intent = reference.get("reference_intent")
    if reference_intent:
        checks.append({"field":"intent","category":"intent","critical":False,"correct":action.get("intent")==reference_intent})
    for field, expected in (reference.get("reference_entities") or {}).items():
        if expected is None or expected == "":
            continue
        checks.append({"field":field,"category":"entity","critical":field in CRITICAL_FIELDS,"correct":_comparable(action.get(field))==_comparable(expected)})
    reference_action = reference.get("reference_action")
    if reference_action:
        checks.append({"field":"required_action","category":"required_action","critical":False,"correct":_comparable(action.get("required_action"))==_comparable(reference_action)})
    if "reference_missing_information" in reference:
        checks.append({"field":"missing_information","category":"missing_information","critical":False,"correct":_comparable(action.get("missing_information", []))==_comparable(reference["reference_missing_information"])})
    if "reference_needs_confirmation" in reference:
        checks.append({"field":"needs_confirmation","category":"safety","critical":False,"correct":action.get("needs_confirmation")==reference.get("reference_needs_confirmation")})
    if "expected_confirmation_fields" in reference:
        checks.append({"field":"confirmation_fields","category":"safety","critical":False,"correct":_comparable(action.get("confirmation_fields", []))==_comparable(reference.get("expected_confirmation_fields", []))})
    correct = sum(1 for check in checks if check["correct"])
    def subset(category=None, critical=None):
        return [c for c in checks if (category is None or c["category"]==category) and (critical is None or c["critical"]==critical)]
    intent=subset("intent"); entities=subset("entity"); critical=subset(critical=True); required_actions=subset("required_action"); missing_checks=subset("missing_information"); safety_checks=subset("safety")
    return {
        "intent_accuracy": sum(c["correct"] for c in intent)/len(intent) if intent else None,
        "intent_correct": sum(c["correct"] for c in intent), "intent_applicable": len(intent),
        "entity_accuracy": sum(c["correct"] for c in entities)/len(entities) if entities else None,
        "entity_correct": sum(c["correct"] for c in entities), "entity_applicable": len(entities),
        "business_action_accuracy": correct/len(checks) if checks else None,
        "business_action_correct": correct, "business_action_applicable": len(checks),
        "critical_entity_accuracy": sum(c["correct"] for c in critical)/len(critical) if critical else None,
        "critical_entity_correct": sum(c["correct"] for c in critical), "critical_entity_applicable": len(critical),
        "required_action_accuracy": sum(c["correct"] for c in required_actions)/len(required_actions) if required_actions else None,
        "required_action_correct": sum(c["correct"] for c in required_actions), "required_action_applicable": len(required_actions),
        "missing_information_accuracy": sum(c["correct"] for c in missing_checks)/len(missing_checks) if missing_checks else None,
        "missing_information_correct": sum(c["correct"] for c in missing_checks), "missing_information_applicable": len(missing_checks),
        "never_guess_accuracy": sum(c["correct"] for c in safety_checks)/len(safety_checks) if safety_checks else None,
        "never_guess_correct": sum(c["correct"] for c in safety_checks), "never_guess_applicable": len(safety_checks),
        "checks": checks,
    }
