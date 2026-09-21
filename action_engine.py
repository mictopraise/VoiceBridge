"""VoiceBridge's ASR-independent business-action intelligence layer."""

from __future__ import annotations

import re
from typing import Any


INTENT_PATTERNS = {
    "PAYMENT_CONFIRMATION": (
        "i paid", "have paid", "payment sent", "transfer sent", "paid already",
        "i don pay", "don pay",
    ),
    "COMPLAINT": ("complain", "complaint", "damaged", "broken", "wrong order", "not working", "disappointed"),
    "ORDER_FOLLOWUP": ("my order", "order status", "follow up", "follow-up", "not arrived", "where is"),
    "DELIVERY_REQUEST": ("deliver", "delivery", "send it to", "bring it to"),
    "NEGOTIATION": ("discount", "last price", "reduce", "cheaper", "best price"),
    "PRICE_ENQUIRY": ("how much", "price", "cost", "charge", "elo ni", "melo ni"),
    "PRODUCT_AVAILABILITY": ("available", "in stock", "do you have", "get am", "you get"),
    "APPOINTMENT_REQUEST": ("appointment", "book a time", "schedule", "see you at"),
    "SERVICE_REQUEST": ("service", "repair", "clean", "wash", "laundry", "design", "create a video"),
    "NEW_ORDER": ("i want", "i need", "i wan", "order", "buy", "purchase"),
    "GENERAL_ENQUIRY": ("information", "details", "tell me", "want to know", "enquiry"),
}

PRODUCTS = (
    "bluetooth headphones", "wireless headphones", "headphones", "earbuds", "phone",
    "cake", "perfume", "lotion", "cream", "shirt", "shoe", "bag", "video",
    "washing", "laundry", "repair", "appointment",
)

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

REQUIRED_ACTIONS = {
    "PRODUCT_AVAILABILITY": "Check product availability and respond to the customer",
    "PRICE_ENQUIRY": "Confirm the current price and respond to the customer",
    "NEW_ORDER": "Review the order details and confirm the order",
    "DELIVERY_REQUEST": "Check delivery availability and confirm the delivery details",
    "ORDER_FOLLOWUP": "Check the order status and update the customer",
    "COMPLAINT": "Review the complaint and contact the customer",
    "SERVICE_REQUEST": "Check service availability and confirm the requirements",
    "APPOINTMENT_REQUEST": "Check the schedule and confirm an appointment",
    "PAYMENT_CONFIRMATION": "Verify the payment independently before confirming",
    "NEGOTIATION": "Review the requested price or discount and respond",
    "GENERAL_ENQUIRY": "Review the enquiry and provide the requested information",
    "UNKNOWN": "Listen to the voice note and clarify the customer's request",
}

CRITICAL_FIELD_LABELS = {
    "amount": "payment amount",
    "quantity": "quantity",
    "product_or_service": "product or service",
    "location": "delivery address or location",
    "date": "date",
    "time": "time",
    "payment_status": "payment status",
    "phone_or_reference": "order or payment reference",
}

REQUIRED_CRITICAL_FIELDS = {
    "PRODUCT_AVAILABILITY": {"product_or_service"},
    "PRICE_ENQUIRY": {"product_or_service"},
    "NEW_ORDER": {"product_or_service", "quantity"},
    "DELIVERY_REQUEST": {"product_or_service", "location"},
    "ORDER_FOLLOWUP": {"phone_or_reference"},
    "SERVICE_REQUEST": {"product_or_service"},
    "APPOINTMENT_REQUEST": {"date", "time"},
    "PAYMENT_CONFIRMATION": {"payment_status"},
    "NEGOTIATION": {"product_or_service"},
}


def _contains(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def detect_languages(text: str, asr_language: str | None = None) -> list[str]:
    lower = f" {text.lower()} "
    languages: list[str] = []
    language_names = {"yo": "Yoruba", "ha": "Hausa", "ig": "Igbo", "en": "English"}
    if asr_language in language_names:
        languages.append(language_names[asr_language])
    if _contains(lower, (" jowo ", " mo fe ", " mo fẹ ", " elo ni ", " e jowo ", " ni mokola ")):
        languages.append("Yoruba")
    if _contains(lower, (" abeg ", " dey ", " una ", " i wan ", " make you ", " no fit ", " you get ")):
        languages.append("Nigerian Pidgin")
    english_markers = re.findall(r"\b(?:i|want|need|please|deliver|price|order|tomorrow|today|the|to)\b", lower)
    if english_markers:
        languages.append("English")
    return list(dict.fromkeys(languages)) or ["Unknown"]


def classify_intent(text: str) -> str:
    lower = text.lower()
    for intent, phrases in INTENT_PATTERNS.items():
        if _contains(lower, phrases):
            return intent
    return "UNKNOWN"


def extract_quantity(text: str) -> int | None:
    lower = text.lower()
    product_group = "(?:bluetooth headphones|wireless headphones|headphones?|earbuds?|phones?|cakes?|perfumes?|lotions?|creams?|shirts?|shoes?|bags?|videos?)"
    gap = r"(?:pieces?\s+|pcs?\s+)?(?:[a-z]+\s+){0,2}"
    digit = re.search(rf"\b(\d{{1,3}})\s+{gap}{product_group}\b", lower)
    if digit:
        return int(digit.group(1))
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\s+{gap}{product_group}\b", lower):
            return value
    pieces = re.search(r"\b(\d{1,3}|" + "|".join(NUMBER_WORDS) + r")\s+(?:pieces?|pcs?)\b", lower)
    if pieces:
        token = pieces.group(1)
        return int(token) if token.isdigit() else NUMBER_WORDS[token]
    return None


def extract_amount(text: str) -> str | None:
    patterns = (
        r"(?:₦|ngn\s*)\s*([0-9][0-9,]*(?:\.\d+)?)",
        r"\b([0-9][0-9,]*(?:\.\d+)?)\s*(?:naira|ngn)\b",
        r"\b([0-9]+(?:\.\d+)?)\s*k\b",
    )
    for index, pattern in enumerate(patterns):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).replace(",", "")
            if index == 2:
                value = str(int(float(value) * 1000))
            return f"₦{int(float(value)):,}"
    return None


def extract_product(text: str) -> str | None:
    lower = text.lower()
    for product in PRODUCTS:
        if re.search(rf"\b{re.escape(product)}s?\b", lower):
            return product.title()
    return None


def extract_location(text: str) -> str | None:
    match = re.search(
        r"\b(?:deliver(?:ed|y)?\s+(?:to|at)|send\s+(?:it\s+)?to|bring\s+(?:it\s+)?to|location\s+(?:is|na))\s+"
        r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' -]{1,45}?)(?=\s+(?:today|tomorrow|on|by|before|please|abeg)\b|[,.!?]|$)",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip().title() if match else None


def extract_date_time(text: str) -> str | None:
    match = re.search(
        r"\b(today|tomorrow|tonight|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
        r"(?:\s+(?:at|by|before)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?))?",
        text,
        re.IGNORECASE,
    )
    if match:
        return " ".join(item for item in match.groups() if item).title()
    clock = re.search(r"\b(?:at|by|before)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b", text, re.IGNORECASE)
    return clock.group(1).upper() if clock else None


def extract_date(text: str) -> str | None:
    match = re.search(
        r"\b(today|tomorrow|tonight|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        text,
        re.IGNORECASE,
    )
    return match.group(1).title() if match else None


def extract_time(text: str) -> str | None:
    match = re.search(
        r"\b(?:at|by|before)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).upper().replace(" ", "")
    period = re.search(r"\b(morning|afternoon|evening|night)\b", text, re.IGNORECASE)
    return period.group(1).title() if period else None


def extract_customer_name(text: str) -> str | None:
    match = re.search(
        r"\b(?:my name is|this is)\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' -]{1,35}?)(?=\s+(?:and|i|calling|from|please)\b|[,.!?]|$)",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip().title() if match else None


def extract_phone_or_reference(text: str) -> str | None:
    phone = re.search(r"(?<!\d)(?:\+?234|0)[789][01]\d{8}(?!\d)", text.replace(" ", ""))
    if phone:
        return phone.group(0)
    reference = re.search(
        r"\b(?:order|reference|ref)\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{4,20})\b",
        text,
        re.IGNORECASE,
    )
    return reference.group(1).upper() if reference else None


def reported_payment_status(text: str, intent: str) -> str | None:
    if intent != "PAYMENT_CONFIRMATION":
        return None
    if _contains(text.lower(), INTENT_PATTERNS["PAYMENT_CONFIRMATION"]):
        return "Customer reports payment sent"
    return None


def field_is_ambiguous(field: str, text: str) -> bool:
    lower = text.lower()
    uncertainty = r"(?:or|/|maybe|perhaps|not sure|unclear|either)"
    patterns = {
        "amount": (
            rf"\b(?:₦|ngn)?\s*\d[\d,]*\s*{uncertainty}\s*(?:₦|ngn)?\s*\d[\d,]*(?:\s*(?:naira|thousand|k))?\b",
            rf"\b[a-z]+\s*{uncertainty}\s*[a-z]+\s+(?:thousand|naira)\b",
            rf"\b[a-z]+\s+(?:thousand|naira)\s*{uncertainty}\s*[a-z]+\s+(?:thousand|naira)\b",
            r"\b(?:about|around|approximately|maybe)\s*(?:₦|ngn)?\s*\d[\d,]*(?:\s*(?:naira|thousand|k))?\b",
        ),
        "quantity": (rf"\b(?:\d+|{'|'.join(NUMBER_WORDS)})\s*{uncertainty}\s*(?:\d+|{'|'.join(NUMBER_WORDS)})\b",),
        "product_or_service": (rf"\b(?:{'|'.join(re.escape(item) for item in PRODUCTS)})s?\s*{uncertainty}\s*(?:{'|'.join(re.escape(item) for item in PRODUCTS)})s?\b",),
        "location": (rf"\b(?:deliver(?:y)?\s+(?:to|at)|send\s+(?:it\s+)?to|bring\s+(?:it\s+)?to)\s+[^,.!?]{{1,35}}\s+{uncertainty}\s+[^,.!?]{{1,35}}",),
        "date": (rf"\b(?:today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*{uncertainty}\s*(?:today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",),
        "time": (rf"\b\d{{1,2}}(?::\d{{2}})?\s*{uncertainty}\s*\d{{1,2}}(?::\d{{2}})?\s*(?:am|pm)\b",),
        "phone_or_reference": (rf"\b(?:order|reference|ref)\s*(?:number|no\.?|#)?\s*[:#-]?\s*[A-Z0-9-]{{4,20}}\s*{uncertainty}\s*[A-Z0-9-]{{4,20}}\b",),
    }
    return any(re.search(pattern, lower, re.IGNORECASE) for pattern in patterns.get(field, ()))


def build_field_state(
    field: str,
    value: Any,
    source: str,
    asr_confidence: float,
    required: bool,
) -> dict[str, Any]:
    label = CRITICAL_FIELD_LABELS[field]
    if field_is_ambiguous(field, source):
        return {
            "value": None,
            "confidence": "low",
            "requires_confirmation": True,
            "reason": f"{label.title()} is ambiguous in the transcript",
        }
    if value is None:
        return {
            "value": None,
            "confidence": "unknown",
            "requires_confirmation": required,
            "reason": (
                f"{label.title()} was not found but is required for this action"
                if required else f"{label.title()} was not provided"
            ),
        }
    if field == "payment_status":
        return {
            "value": value,
            "confidence": "medium",
            "requires_confirmation": True,
            "reason": "Customer-reported payment must be independently verified",
        }
    if asr_confidence < 45:
        return {
            "value": value,
            "confidence": "low",
            "requires_confirmation": True,
            "reason": "Overall speech-recognition confidence is low",
        }
    if asr_confidence < 70:
        return {
            "value": value,
            "confidence": "medium",
            "requires_confirmation": True,
            "reason": "Speech recognition is only moderately confident",
        }
    return {
        "value": value,
        "confidence": "high",
        "requires_confirmation": False,
        "reason": None,
    }


def missing_information(intent: str, entities: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if intent in {"PRODUCT_AVAILABILITY", "PRICE_ENQUIRY", "NEW_ORDER", "DELIVERY_REQUEST", "NEGOTIATION"}:
        if not entities["product_or_service"]:
            missing.append("Exact product or service")
    if intent == "NEW_ORDER" and entities["quantity"] is None:
        missing.append("Quantity")
    if intent == "DELIVERY_REQUEST" and not entities["location"]:
        missing.append("Delivery location")
    if intent == "APPOINTMENT_REQUEST" and not entities["date_or_time"]:
        missing.append("Preferred date or time")
    if intent == "PAYMENT_CONFIRMATION" and not entities["amount"] and not entities["phone_or_reference"]:
        missing.append("Payment amount or reference")
    return missing


def build_reply(action: dict[str, Any]) -> str:
    intent = action["intent"]
    states = action["field_states"]
    confirmation_fields = action["confirmation_fields"]
    if intent == "UNKNOWN":
        return "Thank you for your message. Please clarify what product or service you need so we can assist you correctly."
    if intent == "PAYMENT_CONFIRMATION":
        customer_checks = [field for field in confirmation_fields if field != "payment status"]
        if customer_checks:
            return (
                f"Thank you for the update. Please confirm the {', '.join(customer_checks)} "
                "and share your payment reference. We will independently verify the payment."
            )
        return "Thank you for the update. Please share your payment reference while we independently verify the payment."
    if confirmation_fields:
        requested = ", ".join(confirmation_fields)
        return f"Thank you for your message. Please confirm the {requested} so we can proceed correctly."
    product = states["product_or_service"]["value"]
    quantity = states["quantity"]["value"]
    subject = ""
    if quantity and product:
        display_product = product.lower()
        if quantity != 1 and not display_product.endswith("s"):
            display_product += "s"
        subject = f" for {quantity} {display_product}"
    elif product:
        subject = f" about {product.lower()}"
    reply = f"Thank you. We received your {intent.lower().replace('_', ' ')}{subject}."
    reply += " We will check the details and respond shortly."
    return reply


def build_safe_required_action(
    intent: str, field_states: dict[str, dict[str, Any]]
) -> tuple[str, list[str]]:
    required = REQUIRED_CRITICAL_FIELDS.get(intent, set())
    risky = [
        field for field in required
        if field_states[field]["requires_confirmation"]
    ]
    if intent == "PAYMENT_CONFIRMATION":
        return "Verify payment status independently before confirming the order", ["payment status"]
    if risky:
        labels = [CRITICAL_FIELD_LABELS[field] for field in risky]
        return (
            f"Confirm {', '.join(labels)} with the customer before taking business action",
            labels,
        )
    return REQUIRED_ACTIONS[intent], []


def analyze_business_action(
    transcript: str,
    english: str | None = None,
    asr_language: str | None = None,
    asr_confidence: int | float | None = None,
) -> dict[str, Any]:
    source = (english or transcript or "").strip()
    intent = classify_intent(source)
    entities = {
        "product_or_service": extract_product(source),
        "quantity": extract_quantity(source),
        "amount": extract_amount(source),
        "location": extract_location(source),
        "date_or_time": extract_date_time(source),
        "customer_name": extract_customer_name(source),
        "phone_or_reference": extract_phone_or_reference(source),
    }
    missing = missing_information(intent, entities)
    confidence_value = float(asr_confidence) if asr_confidence is not None else 0.0
    confidence = "High" if confidence_value >= 75 else "Medium" if confidence_value >= 45 else "Low"
    dates = {
        "date": extract_date(source),
        "time": extract_time(source),
    }
    payment_status = reported_payment_status(source, intent)
    required_fields = REQUIRED_CRITICAL_FIELDS.get(intent, set())
    critical_values = {
        "amount": entities["amount"],
        "quantity": entities["quantity"],
        "product_or_service": entities["product_or_service"],
        "location": entities["location"],
        "date": dates["date"],
        "time": dates["time"],
        "payment_status": payment_status,
        "phone_or_reference": entities["phone_or_reference"],
    }
    field_states = {
        field: build_field_state(
            field, value, source, confidence_value, field in required_fields
        )
        for field, value in critical_values.items()
    }
    for field in ("amount", "quantity", "product_or_service", "location", "phone_or_reference"):
        entities[field] = field_states[field]["value"]
    dates = {
        "date": field_states["date"]["value"],
        "time": field_states["time"]["value"],
    }
    if dates["date"] or dates["time"]:
        entities["date_or_time"] = " ".join(
            value for value in (dates["date"], dates["time"]) if value
        )
    else:
        entities["date_or_time"] = None
    safe_action, required_confirmation_fields = build_safe_required_action(intent, field_states)
    confirmation_fields = [
        CRITICAL_FIELD_LABELS[field]
        for field, state in field_states.items()
        if state["requires_confirmation"] and (
            state["value"] is not None
            or field in required_fields
            or state["confidence"] == "low"
        )
    ]
    confirmation_fields = list(dict.fromkeys(required_confirmation_fields + confirmation_fields))
    missing_labels = {
        "quantity": "Quantity",
        "product_or_service": "Exact product or service",
        "location": "Delivery location",
        "date": "Preferred date or time",
        "time": "Preferred date or time",
    }
    for field in required_fields:
        if field_states[field]["value"] is None and field in missing_labels:
            label = missing_labels[field]
            if label not in missing:
                missing.append(label)
    action = {
        "languages": detect_languages(f"{transcript} {english or ''}", asr_language),
        "intent": intent,
        "customer_request": source or None,
        **entities,
        **dates,
        "payment_status": field_states["payment_status"]["value"],
        "urgency": "Urgent" if _contains(source.lower(), ("urgent", "asap", "immediately", "now now")) else None,
        "required_action": safe_action,
        "missing_information": missing,
        "confidence": confidence,
        "field_states": field_states,
        "confirmation_fields": confirmation_fields,
        "needs_confirmation": any(
            state["requires_confirmation"] for state in field_states.values()
        ),
        "suggested_reply": "",
    }
    action["suggested_reply"] = build_reply(action)
    return action
