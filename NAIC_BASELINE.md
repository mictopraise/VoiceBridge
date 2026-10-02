# NAIC 2026 baseline

This checkpoint records the executable VoiceBridge baseline before N-ATLAS is
introduced. It intentionally changes no production behavior.

- Branch: `naic-2026-natlas`
- Python: 3.12
- Application entry point: `app.py`
- ASR contract: `speech_engines.base.ASRResult`
- Current product ASR: local faster-whisper
- Current English meaning: a separate faster-whisper translation pass
- Remote provider support: Sahara saved-response normalization and protected
  provider cache
- Downstream ownership: VoiceBridge Action Engine and Never-Guess safeguards

The regression suite uses mocks and synthetic audio. It does not download
models, call external providers, or commit private recordings. Frozen Sahara
benchmark evidence is not modified by this baseline restoration.
