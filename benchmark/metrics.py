"""Transparent speech-error metrics for the VoiceBridge benchmark."""

from __future__ import annotations

import re
import unicodedata
from typing import Sequence, TypeVar

T = TypeVar("T")


def normalize_text(text: str, mode: str = "standard") -> str:
    normalized = unicodedata.normalize("NFC", text or "").casefold()
    normalized = re.sub(r"(?<=\d),(?=\d)", "", normalized)
    if mode == "strict":
        return " ".join(normalized.split())
    if mode != "standard":
        raise ValueError("Normalization mode must be 'standard' or 'strict'.")
    normalized = re.sub(r"\bngn\b|₦", " naira ", normalized)
    output = []
    for character in normalized:
        category = unicodedata.category(character)
        if character in {"'", "’", "-"}:
            output.append("'" if character == "’" else character)
        elif category.startswith("P") or category.startswith("S"):
            output.append(" ")
        else:
            output.append(character)
    return " ".join("".join(output).split())


def edit_distance(reference: Sequence[T], hypothesis: Sequence[T]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, reference_item in enumerate(reference, start=1):
        current = [row]
        for column, hypothesis_item in enumerate(hypothesis, start=1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (reference_item != hypothesis_item),
            ))
        previous = current
    return previous[-1]


def error_rate(reference: Sequence[T], hypothesis: Sequence[T]) -> float:
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return edit_distance(reference, hypothesis) / len(reference)


def wer(reference: str, hypothesis: str, mode: str = "standard") -> float:
    return error_rate(normalize_text(reference, mode).split(), normalize_text(hypothesis, mode).split())


def cer(reference: str, hypothesis: str, mode: str = "standard") -> float:
    return error_rate(list(normalize_text(reference, mode).replace(" ", "")), list(normalize_text(hypothesis, mode).replace(" ", "")))


def speech_metrics(reference: str, hypothesis: str) -> dict[str, float | int]:
    output: dict[str, float | int] = {}
    for mode, prefix in (("standard", ""), ("strict", "strict_")):
        reference_text = normalize_text(reference, mode)
        hypothesis_text = normalize_text(hypothesis, mode)
        reference_words = reference_text.split()
        hypothesis_words = hypothesis_text.split()
        reference_chars = list(reference_text.replace(" ", ""))
        hypothesis_chars = list(hypothesis_text.replace(" ", ""))
        word_errors = edit_distance(reference_words, hypothesis_words)
        character_errors = edit_distance(reference_chars, hypothesis_chars)
        output.update({
            f"{prefix}wer": error_rate(reference_words, hypothesis_words),
            f"{prefix}cer": error_rate(reference_chars, hypothesis_chars),
            f"{prefix}word_errors": word_errors,
            f"{prefix}reference_words": len(reference_words),
            f"{prefix}character_errors": character_errors,
            f"{prefix}reference_characters": len(reference_chars),
        })
    return output
