"""Deterministic disagreement signals for Dual N-ATLAS Review.

This module never selects a correct transcript, merges provider output, or creates a
confidence score.  It only identifies differences that should be shown to a human.
"""

from __future__ import annotations

from difflib import SequenceMatcher
import re
import unicodedata


NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "twenty", "thirty", "forty", "fifty",
    "hundred", "thousand", "million",
}
DATE_WORDS = {
    "today", "tomorrow", "yesterday", "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "sunday", "week", "month",
}
TIME_WORDS = {"morning", "afternoon", "evening", "night", "am", "pm", "noon"}
PAYMENT_WORDS = {"pay", "paid", "payment", "transfer", "transferred", "deposit"}
NEGATIONS = {"no", "not", "never", "dont", "don't", "didnt", "didn't", "ko", "kò"}
ACTION_WORDS = {
    "buy", "order", "deliver", "send", "book", "cancel", "return", "refund",
    "replace", "repair", "collect", "confirm", "pay", "paid", "need", "want",
}
LOCATION_CUES = {"to", "at", "address", "location", "deliver", "delivery"}
STOPWORDS = {
    "a", "an", "and", "are", "as", "be", "for", "from", "i", "in", "is",
    "it", "me", "my", "of", "on", "please", "the", "this", "that", "we",
    "you", "your", "abeg", "want", "need", "send", "deliver", "order",
} | NUMBER_WORDS | DATE_WORDS | TIME_WORDS | PAYMENT_WORDS | NEGATIONS


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", str(text or "")).casefold()
    return re.findall(r"[\w₦'-]+", normalized, flags=re.UNICODE)


def _values(tokens: list[str], vocabulary: set[str], *, numeric: bool = False) -> list[str]:
    found = {
        token for token in tokens
        if token in vocabulary or (numeric and bool(re.fullmatch(r"\d+(?:[.,]\d+)?", token)))
    }
    return sorted(found)


def _location_terms(tokens: list[str]) -> list[str]:
    found = set()
    for index, token in enumerate(tokens[:-1]):
        if token in LOCATION_CUES:
            for candidate in tokens[index + 1:index + 4]:
                if candidate not in STOPWORDS and not candidate.isdigit():
                    found.add(candidate)
    return sorted(found)


def _content_terms(tokens: list[str]) -> list[str]:
    return sorted({
        token for token in tokens
        if len(token) > 2 and token not in STOPWORDS and not token.isdigit()
        and token not in ACTION_WORDS and token not in LOCATION_CUES
    })


def compare_transcripts(yoruba_transcript: str, english_transcript: str) -> dict:
    """Return auditable disagreement categories without judging either model."""
    yo_tokens = _tokens(yoruba_transcript)
    en_tokens = _tokens(english_transcript)
    categories = {}

    extractors = {
        "numbers_or_quantities": lambda value: _values(value, NUMBER_WORDS, numeric=True),
        "dates": lambda value: _values(value, DATE_WORDS),
        "times": lambda value: _values(value, TIME_WORDS),
        "payment_claims": lambda value: _values(value, PAYMENT_WORDS),
        "negations": lambda value: _values(value, NEGATIONS),
        "material_actions": lambda value: _values(value, ACTION_WORDS),
        "locations_or_addresses": _location_terms,
        "product_or_service_terms": _content_terms,
    }
    for name, extractor in extractors.items():
        left = extractor(yo_tokens)
        right = extractor(en_tokens)
        if left != right and (left or right):
            categories[name] = {"yoruba_model": left, "nigerian_english_model": right}

    money_markers = {"₦", "naira", "ngn"}
    yo_money = sorted(set(_values(yo_tokens, money_markers)) | set(
        _values(yo_tokens, set(), numeric=True) if set(yo_tokens) & money_markers else []
    ))
    en_money = sorted(set(_values(en_tokens, money_markers)) | set(
        _values(en_tokens, set(), numeric=True) if set(en_tokens) & money_markers else []
    ))
    if yo_money != en_money and (yo_money or en_money):
        categories["money_or_amounts"] = {
            "yoruba_model": yo_money, "nigerian_english_model": en_money,
        }

    similarity = SequenceMatcher(None, yo_tokens, en_tokens).ratio() if (yo_tokens or en_tokens) else 1.0
    if yo_tokens and en_tokens and similarity < 0.55:
        categories["substantial_transcript_divergence"] = {
            "yoruba_model": [], "nigerian_english_model": [],
        }
    return {
        "material_disagreement": bool(categories),
        "review_required": bool(categories),
        "categories": categories,
        "token_similarity_for_routing_only": round(similarity, 4),
        "confidence": None,
        "correct_model": None,
        "notice": (
            "Model disagreement detected — human review required."
            if categories else
            "No material disagreement detected by the deterministic rules. This is not proof of correctness."
        ),
    }
