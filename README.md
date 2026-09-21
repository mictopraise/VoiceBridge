# VoiceBridge — From African Voice Notes to Business Action

This safety update withholds the suggested business reply when transcription or translation confidence is below 45%. Correct the editable English meaning first, then regenerate the reply.

VoiceBridge converts natural African customer voice notes into an editable transcript, English meaning and a structured business Action Card. The competition build focuses on English, Nigerian Pidgin, Yoruba and their code-switched combinations. Local processing uses Whisper; the Sahara adapter now normalizes preserved finalized provider responses through the same downstream logic.

## What VoiceBridge adds

VoiceBridge does not develop or claim ownership of the underlying speech-recognition foundation models. It provides:

- ASR-independent orchestration
- African code-switch analysis
- a business-intent taxonomy
- structured business entity extraction
- missing-information and confirmation signals
- voice-to-action transformation
- local fallback architecture
- a customer-operations Action Card and editable response
- an original downstream business-action benchmark design

These project contributions remain the same whether the transcript comes from Sahara or Whisper.

## M2.5 Benchmark foundation

Speech providers now return a common `ASRResult` containing the engine and model identity, transcript, detected language, segments, audio duration, processing time and provider metadata. The existing product route uses the Whisper adapter through a compatibility wrapper, so M0-M2 behavior remains intact.

The benchmark harness runs the same manifest and scoring code for every requested provider. It records provider failures instead of silently substituting Whisper. It reports corpus WER/CER, strict orthographic variants, downstream business-action accuracy, critical-entity accuracy, Never-Guess accuracy, latency and real-time factor. See `benchmark/README.md`.

## M2.7 Evidence build

VoiceBridge-CSBiz v1 defines 13 reproducible Nigerian SME scenarios spanning
English, Nigerian Pidgin, Yoruba and code-switched combinations. Its transcript-level
baseline is explicitly labeled as an oracle evaluation of VoiceBridge's downstream
logic, not an ASR benchmark. Recorded audio remains pending and cannot be presented
as human or synthetic evidence until its source and consent status are recorded.

After the two justified M2.8 regression corrections, the measured downstream
baseline is 100% across intent, entity, critical-entity, required-action,
missing-information, Never-Guess and overall Business Action Accuracy across 13
authoritative transcripts. This remains an oracle transcript-level result, not
ASR or end-to-end accuracy. Raw results are under `benchmark/results/csbiz_text_v1/`.

## M2.8–M2.9 real-audio evidence

Three private Owner recordings were processed through the identical benchmark
pipeline with faster-whisper `large-v3` and multilingual `small`. Large-v3 reached
25.88% WER versus Small's 52.94% on this limited flagship set; both local systems
are transparently members of the Whisper family. The raw transcripts show why
VoiceBridge separately measures business outcomes: Large-v3 changed Pidgin
`I don pay` to `I don't pay`, reversing the payment meaning.

The Sahara adapter supports secret environment configuration, content hashing,
deterministic request identities, immutable success caching, raw/normalized
result persistence and no-auto-retry failure logs. One Owner-submitted Sample A
result has been normalized and scored from its preserved `FILE_TRANSCRIBED`
response. M3 made no additional provider request.

## M1 Business Action Engine

The current competition branch supports the initial intent taxonomy and extracts product/service, quantity, amount, customer name, phone/reference, location, date/time, urgency and required action. Fields unsupported by the transcript remain `null` or are listed as missing. The browser displays the result in a VoiceBridge Action Card, and edits to the transcript or English meaning can regenerate the action.

## M2 Never-Guess safety

Critical business fields now include a categorical safety state: value, confidence, confirmation requirement and reason. Ambiguous values become unknown instead of being silently selected. Required actions pause for necessary confirmation, customer-reported payments require independent verification, and suggested replies do not repeat uncertain values as facts. See `SAFETY.md` for the inspectable policy.

## What you need

- Windows 10 or 11
- Python 3.12 from https://www.python.org/downloads/
- Internet for the first installation and first model download
- Approximately 2 GB of free disk space

During Python installation, tick **Add Python to PATH**.

Python 3.12 can be installed alongside Python 3.14. VoiceBridge explicitly
uses 3.12 and will not replace or modify the newer installation.

## Start the app

1. Extract this folder.
2. Double-click `start_windows.bat`.
3. On the first run, allow installation to complete. The speech model will download automatically.
4. Your browser opens at http://127.0.0.1:5050.
5. Upload a WhatsApp voice note and select **Transcribe and translate**.

For short voice notes, select the known spoken language (for example, Hausa)
rather than automatic detection. Short clips do not provide enough speech for
reliable language identification.

Use **Medium — more accurate** for difficult or very short regional-language
notes. The first Medium run downloads a larger model and will take longer.

Use **Large v3** only when Small and Medium remain inaccurate. It offers the
best available local Whisper accuracy but is much slower and requires several
gigabytes of storage and memory.

Version 0.2 preprocesses each recording locally into normalized 16 kHz mono
audio, reports an estimated confidence level and lets you correct both the
original transcript and English meaning. After correcting the English meaning,
select **Regenerate reply from edited English** before copying the response.

Later launches are much faster because the software and model are already stored locally.

## Privacy

Uploaded voice notes are placed in a temporary file and deleted immediately after processing. The app listens only on your computer (`127.0.0.1`) and is not publicly accessible.

## Current competition-build limitations

- Speech quality depends on background noise, accent and recording clarity.
- Action extraction has a 13-case oracle regression baseline and a three-clip
  end-to-end proof, but neither sample set supports broad accuracy claims.
- Entity extraction is deliberately conservative and still needs broader product and phrasing coverage.
- Categorical field confidence is a conservative policy signal, not calibrated probability.
- Sahara completed 19 of the 20 frozen AfriSwitch samples; one finalized result
  contained an empty transcript and remains counted as a failure. The exact
  provider model/version and processing latency were not exposed, so no Sahara
  latency comparison is claimed.
- Confidence is an estimate, not a guarantee. Always listen and review names,
  amounts and product details before sending a response.
- This version is for business validation, not yet a public customer-facing service.

## Final competition status

The benchmark and submission materials are prepared. Owner must record and
validate the final demo, insert public/unlisted demo and repository URLs, run
the signed-out access checks in `SUBMISSION_AUDIT.md`, and retain sole authority
for the one permitted competition submission.