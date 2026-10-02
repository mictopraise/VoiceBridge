# VoiceBridge NAIC field testing

The local field-testing page is available at:

`http://127.0.0.1:5050/field-testing`

It is a companion to the VoiceBridge product workflow. It does not change ASR,
translation, Action Engine, Never-Guess, or benchmark behavior.

## Privacy boundary

- Use participant codes, not names.
- Do not enter phone numbers or exact addresses.
- Do not attach or link raw recordings.
- Confirm consent before saving an interaction.
- The default local log is `local_data/field_testing/interactions.json` and is
  excluded from Git.
- Set `VOICEBRIDGE_FIELD_TEST_LOG` to use another private local path.
- Full CSV and JSON exports contain participant codes, feedback and notes and
  must remain private.
- The sanitized summary contains aggregate counts only. It excludes participant
  codes, free-text feedback, tester notes, audio and direct identifiers.

Historic benchmark clips are not field interactions and must not be entered.

## Target mix

| Language or mix | Target |
| --- | ---: |
| Nigerian-accented English | 20 |
| Yoruba | 15 |
| Yoruba-English | 10 |
| Pidgin-English using explicitly selected Whisper | 5 |

## Exports

- `/field-testing/export.csv` — complete private CSV
- `/field-testing/export.json` — complete private JSON
- `/field-testing/sanitized-summary.json` — aggregate submission-safe JSON

Interaction identifiers are assigned sequentially as `VB-001`, `VB-002`, and
so on. Writes are atomic to avoid leaving a partly written local log.
