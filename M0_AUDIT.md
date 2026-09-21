# M0 Baseline Audit

Date: 14 September 2026

## Preserved baseline

- Product: VoiceBridge NG v0.2.1
- Baseline branch: `main`
- Baseline commit: `a314d20`
- Competition branch: `sahara-challenge`
- Runtime: Python 3.12, Flask, faster-whisper, PyAV and NumPy
- Network exposure: local only (`127.0.0.1:5050`)
- Upload limit: 25 MB
- Accepted formats: OPUS, OGG, MP3, M4A, WAV, WEBM and MP4

## Confirmed baseline behavior

- Audio is decoded, trimmed and normalized to 16 kHz mono.
- Whisper supports Small, Medium and Large-v3 selections.
- The user may force Hausa, Yoruba, Igbo or English/Nigerian Pidgin.
- Transcripts and English meanings are editable.
- Low-confidence results do not automatically expose a generic reply.
- Temporary uploaded and processed audio files are deleted after processing.

## Known baseline limitations

- Whisper produced an unreliable Hausa result at 34% confidence on a real short voice note.
- The original reply generator used a few keyword branches and did not create structured business actions.
- No ASR adapter interface or Sahara integration exists yet.
- No benchmark runner or labeled VoiceBridge-CSBiz dataset exists yet.
- The extracted baseline was not a Git repository; M0 created an isolated repository and preserved it in the baseline commit above.

## M0 decision

Preserve the functioning ASR pipeline. Add competition capabilities as independent modules on `sahara-challenge`; do not destructively rewrite the baseline.
