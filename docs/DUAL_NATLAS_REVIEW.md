# Dual N-ATLAS Review

Dual N-ATLAS Review is an additive human-review mode. One normalized recording is
processed sequentially by `NCAIR1/Yoruba-ASR` and
`NCAIR1/NigerianAccentedEnglish`. VoiceBridge preserves both raw outputs and never
labels either one as correct.

## Execution and memory

The existing `NAtlasEngine` is reused. Yoruba runs first. When the Nigerian English
model is requested, the adapter drops its reference to the Yoruba pipeline and runs
garbage collection before loading the second pipeline. The two CPU inference
pipelines are therefore not intentionally resident or executed concurrently.
Downloaded Hugging Face files remain available through the normal on-disk model
cache. No Whisper fallback, translation, chunking, or transcript merge occurs.

## Deterministic disagreement rules

`dual_natlas.compare_transcripts` compares Unicode-NFC, case-folded word tokens and
raises a human-review signal when the two outputs differ on any non-empty category:

- numbers or English number words (quantity-sensitive);
- currency markers and the numbers in a currency-bearing transcript;
- relative days, weekdays, or other configured date words;
- configured time-of-day words;
- location/address candidates following deterministic location cues;
- payment words;
- negation words;
- configured material action verbs;
- remaining non-stopword product/service candidates; or
- substantial whole-transcript divergence (token sequence similarity below 0.55).

These deliberately conservative rules are routing signals, not accuracy metrics.
The internal sequence similarity is not shown as provider confidence. Agreement is
not proof of correctness, and disagreement does not determine which model is right.

## Partial failures

If one model fails, its failure state is shown beside the successful immutable
output and human review is mandatory. If both fail, processing ends with no hidden
fallback. The existing 30-second N-ATLAS limit remains in force.

## Field testing

A dual run has `processing_mode = dual_natlas_review`. It creates one recording
identity and one genuine interaction, with two model-evaluation entries. The human
chooses a successful output as the editable working-transcript starting point.
That provenance is retained. Raw transcript copies are not written to the private
field-test log unless the existing explicit transcript-retention option is selected.
No Action Card or suggested reply is presented as current before this selection.
Selecting Nigerian English seeds the editable English meaning with that English
transcript; selecting Yoruba leaves English meaning blank and runs transcript-only
analysis until a human supplies or verifies an English meaning.
