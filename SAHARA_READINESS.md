# Sahara Integration and Batch Readiness

One saved Sahara Sample A result is integrated. M3 maps the verified
`FILE_TRANSCRIBED` response field `audio_transcript` into the provider-neutral
`ASRResult`; it does not implement or invoke a new upload request.

## Implemented readiness shell

- credential lookup through `VOICEBRIDGE_SAHARA_API_KEY` without logging its value;
- configurable cache root through `VOICEBRIDGE_SAHARA_CACHE_DIR`;
- SHA-256 audio hashing;
- deterministic identity across engine, model, audio bytes and request options;
- immutable successful-result cache to prevent duplicate successful calls;
- raw response plus normalized `ASRResult` persistence;
- finalized saved-response normalization with explicit status validation;
- failure-event persistence with `auto_retry: false`;
- benchmark-level latency and provider failure recording;
- no hidden provider fallback.

The exact Sahara model/version, provider confidence and processing latency were
not exposed in the saved artifacts and are not invented. See `EVIDENCE_LEDGER.md`.

## Still-required documentation review

- official base URL and transcription endpoint;
- authentication header and environment-variable name;
- supported formats, duration and file-size limits;
- language/code-switch controls;
- response schema, model/version identifier and confidence fields;
- quota, cost, timeout and rate-limit behavior;
- data retention/privacy terms.

## Completed Sample A protocol

1. Owner supplied one consented 16-second Sample A request externally.
2. Smartie reused the saved upload and final-status responses; no request was repeated.
3. The exact audio bytes were hashed before cache identity creation.
4. Raw responses and normalized output were stored without a credential.
5. The normalized transcript was passed to the frozen Action Engine and benchmark.
6. The integration stopped before the AfriSwitch batch for review.

## Benchmark rule

Sahara failure must remain a Sahara failure. Benchmark mode must never substitute Whisper. Product mode may later offer local fallback explicitly, but that output must retain the actual engine identity.

## Security

Never commit or print API keys, access codes, login tokens or full authorization headers. Redact provider errors if they can contain request headers or signed URLs.