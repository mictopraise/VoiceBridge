# Never-Guess Safety Layer

VoiceBridge separates a value extracted from speech from a value safe enough to drive business action.

## Critical fields

M2 protects amount, quantity, product/service, location, date, time, payment status and order/payment reference. Every field has:

```json
{
  "value": null,
  "confidence": "unknown",
  "requires_confirmation": true,
  "reason": "Payment amount was not found but is required for this action"
}
```

Confidence is categorical because the current ASR pipeline does not provide defensible token-to-entity probabilities. VoiceBridge does not manufacture numerical field confidence.

## Decision rules

1. An explicitly ambiguous field becomes `null`, even when a regex could choose one candidate.
2. An extracted field from ASR below 45% is low-confidence and requires confirmation.
3. An extracted field from ASR between 45% and 69% is medium-confidence and requires confirmation.
4. A clear extracted field at 70% or higher is high-confidence unless an ambiguity cue is present.
5. A required field that is absent is unknown and requires confirmation.
6. Customer-reported payment is never treated as verified payment.
7. Unsafe values are excluded from suggested replies and actionable flat fields.

These rules are a transparent safety baseline, not a claim that confidence guarantees correctness. Human review remains mandatory for transactions.

## ASR independence

The safety layer accepts normalized transcript text and overall ASR confidence. It contains no Sahara-, Whisper- or Model3-specific fields, so all future speech engines can use the same policy and benchmark.
