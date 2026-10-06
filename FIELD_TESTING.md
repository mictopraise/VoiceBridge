# VoiceBridge NAIC field testing

The local field-testing page is available at:

`http://127.0.0.1:5050/field-testing`

It is a companion to the VoiceBridge product workflow. It does not change ASR,
translation, Action Engine, Never-Guess, or benchmark behavior.

## Integrated workflow

1. Process one recording on `/` with an explicitly selected provider.
2. Review or correct the working transcript and English meaning.
3. Select **Log This Interaction**. The review opens in a new tab, while the
   inference result remains open in the original tab.
4. Verify the actual language mix and complete the human scores. No positive
   score or consent choice is selected automatically.
5. Confirm consent and save.

The inference handoff uses a random, in-memory draft that expires after 30
minutes. Transcript text is never placed in the URL. The original transcript,
edited transcript and English meaning are visible during review but are not
written to the field-test log unless the owner explicitly selects the private
transcript-retention checkbox.

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
- `processed.json` contains only local recording identity and provider/model run
  metadata, never transcript or audio content.

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
- `/field-testing/recording-manifest.csv` — non-destructive recording/code,
  processing and review-status reconciliation export

Interaction identifiers are assigned sequentially as `VB-001`, `VB-002`, and
so on. These logger-generated IDs remain separate from filename audio codes such
as `VB-001_originalfilename.ogg`.

One recording counts as one genuine interaction. A different provider/model run
can be appended as a comparison, and a repeated same-model run can be appended
as an intentional retest. Both remain in evaluation history without increasing
the genuine-interaction count. Ordinary duplicate saves are blocked. Writes are
atomic to avoid leaving a partly written local log.
