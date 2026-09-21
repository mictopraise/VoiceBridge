# VoiceBridge NG changelog

## Competition polish - 15 September 2026

- Reconciled historical oracle, current oracle and real-audio downstream evidence.
- Finalized the Ethics and Inclusion note, demo script, submission-form text and compliance audit.
- Generated and visually validated the maximum three-page benchmark PDF.
- Updated repository positioning and architecture to reflect the frozen three-model benchmark.

## Sahara AfriSwitch benchmark integration — 15 September 2026

- Verified and scored the owner-local Sahara result bundle entirely offline.
- Accounted for all 20 frozen samples: 19 transcripts and one terminal empty
  transcript retained in the corpus denominator.
- Added machine-readable Sahara sample, model and language results and completed
  the three-model comparison without inventing unavailable provider latency.
- Preserved historical TLS failures as provenance while recognizing their two
  explicitly authorized successful retries as current results.

## Sahara final-empty recovery hardening — 15 September 2026

- Classified finalized Sahara responses with empty transcripts as terminal
  per-sample benchmark failures instead of crashing the batch.
- Preserved upload/status payload paths, file ID, processing status, audio hash,
  language, exception and timestamp in durable `FINAL_EMPTY_TRANSCRIPT` records.
- Made normal resume skip terminal empty-transcript results without resubmission
  while continuing later untouched samples.

## Sahara TLS recovery hardening — 15 September 2026

- Isolated upload and polling network failures per sample so later untouched
  samples continue.
- Added durable ambiguous-failure records with sample identity, audio hash,
  language, exception, timestamp and no-auto-retry state.
- Added deterministic recovery of existing finalized responses and explicit
  owner-authorized `--retry-sample` handling.
- Pre-blocked the owner-reported repeated TLS failure at the verified tenth
  frozen sample so normal resume does not submit it again.

## Sahara owner-runner import fix — 14 September 2026

- Replaced eager speech-provider imports with lazy provider loading.
- Removed the Sahara runner's accidental dependency on `av` and
  `faster-whisper` while preserving the existing provider registry API.
- Added a subprocess regression test proving the Sahara runner import does not
  load Whisper-only dependencies.

## Sahara Challenge M3.1 split benchmark — 14 September 2026

- Verified the frozen 20-sample AfriSwitch subset: 10 Yoruba, 10 Nigerian Pidgin and 188.524 seconds.
- Added an ASR-only runner so arbitrary AfriSwitch speech is not assigned fabricated business-action labels.
- Measured complete Large-v3 and Small multilingual CPU/int8 baselines with sample transcripts, corpus-weighted WER/CER, strict metrics and RTF.
- Added a manifest-locked, content-addressed, no-silent-retry Sahara batch runner for execution on the owner's credentialed PC.

## Sahara Challenge M3 — 14 September 2026

- Normalized the preserved `FILE_TRANSCRIBED` Sahara Sample A result without a new API call.
- Recorded real Sahara WER/CER and downstream results using the frozen benchmark logic.
- Created a content-addressed successful provider cache entry with raw upload/status responses.
- Added evidence and run ledgers with source hashes, unavailable-metadata disclosure and no credentials.
- Recorded public competition-demo consent while keeping raw audio private.
- Preserved the frozen 20-sample AfriSwitch manifest without starting the batch.

## Sahara Challenge M2.9 — 14 September 2026

- Ran multilingual Whisper Small on the same three recordings and frozen references.
- Added a real Large-v3 versus Small comparison with critical-token analysis.
- Added provider-neutral audio hashing and deterministic cache identities.
- Added immutable successful-response caching, raw/normalized persistence and failure logging.
- Added environment-variable Sahara credential/cache configuration without inventing its API schema.

## Sahara Challenge M2.8 preparation — 14 September 2026

- Added authoritative, consent-pending ground truth for three flagship audio cases.
- Corrected negotiation precedence without changing the accepted intent taxonomy.
- Made ambiguous required quantity visible in both confirmation and missing-information states.
- Added support for separated “three pieces,” `delivered to`, and named periods such as afternoon.
- Added regression coverage; the suite now contains 36 passing tests.
- No real-audio, Whisper, Sahara or end-to-end result is claimed until recordings are supplied.

## Sahara Challenge M2.8 real-audio proof — 14 September 2026

- Recorded private benchmark consent and Tecno Spark 9T metadata for three Owner clips.
- Corrected an upload filename/content reversal without altering the original uploads.
- Ran faster-whisper Large-v3 on all three clips with automatic language detection and no fallback.
- Preserved raw transcripts, WER/CER, latency, downstream actions and failed checks.
- Public-demo consent remains pending; raw human voice files remain excluded from Git.

## Sahara Challenge M2.7 — 14 September 2026

- Added 13 labeled VoiceBridge-CSBiz Nigerian SME scenarios and consent-aware validation.
- Added a transcript-level downstream runner with explicit oracle/ASR labeling.
- Measured intent, entity, critical-entity, required-action, missing-information,
  Never-Guess and overall Business Action Accuracy without inventing audio results.
- Preserved two observed downstream failures instead of tuning against the benchmark.
- Added recording, ethics, submission-audit, Sahara-readiness, report and demo artifacts.
- Time-boxed Meta OmniCTC dependency setup and recorded it as blocked without claiming inference.

## Sahara Challenge M2.5 — 14 September 2026

- Added a normalized provider-independent speech result contract.
- Routed existing faster-whisper processing through a Whisper adapter without changing the product response contract.
- Added explicit unconfigured Sahara and unselected Model 3 providers; benchmark mode never falls back silently.
- Added JSONL manifest validation and reproducible raw/model/language/downstream outputs.
- Added transparent standard and strict WER/CER with Yoruba diacritics preserved.
- Added corpus-weighted business-action, critical-entity and Never-Guess scoring plus latency and real-time factor.
- Added dataset readiness and Model 3 decision records without downloading large resources.

## Sahara Challenge M2 — 14 September 2026

- Added categorical field-level safety states for eight critical business fields.
- Added explicit ambiguity detection and removal of unsafe actionable values.
- Added payment-verification protection and adaptive required actions.
- Prevented suggested replies from repeating uncertain critical values.
- Added highly visible confirmation styling to the Action Card.
- Added Never-Guess policy documentation and seven required safety tests.

## Sahara Challenge M1 — 14 September 2026

- Preserved v0.2.1 as a baseline Git commit and isolated competition work.
- Added an ASR-independent structured Business Action Engine.
- Added initial intent classification, entity extraction, language cues, missing-information detection and required actions.
- Added an editable VoiceBridge Action Card and `/analyze-action` endpoint.
- Added M0 audit and architecture documentation.

## v0.2.1 — 12 September 2026

- Suppressed automatic business replies when transcription confidence is below 45%.
- Low-confidence results now require a human-corrected English meaning before reply generation.

## v0.2 — 12 September 2026

- Added local 16 kHz mono audio normalization and quiet-edge trimming.
- Added confidence scoring and actionable review warnings.
- Added editable original transcript and English-meaning fields.
- Added reply regeneration from the user's corrected English meaning.
- Added Large v3 as an optional high-accuracy local model.
- Updated Windows startup to verify requirements on every launch.
- Added automated checks for target languages, forced Hausa handling and price replies.

VoiceBridge remains a private validation MVP. Confidence is advisory, and users
must verify names, prices and other important details before sending a reply.