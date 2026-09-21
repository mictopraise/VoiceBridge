# VoiceBridge Final Submission Compliance Audit

Status values: `PASS`, `IN PROGRESS`, `BLOCKED`. Submission is forbidden while any mandatory gate is not `PASS`.

| Gate | Requirement | Status | Evidence / remaining action |
| ---: | --- | --- | --- |
| 1 | Sahara genuinely used | PASS | Real Sample A plus 20-sample owner-local benchmark evidence |
| 2 | Three speech models measured | PASS | Sahara, Whisper Large-v3 and Whisper Small on identical frozen samples |
| 3 | Code-switching visibly demonstrated | IN PROGRESS | Real consented samples ready; final video must capture one |
| 4 | Downstream task shown | IN PROGRESS | Action Card works; final demo capture pending |
| 5 | Benchmark PDF <=3 pages | PASS | Final PDF generated and page-count validated |
| 6 | WER/CER per language present | PASS | Frozen overall and Yoruba/Pidgin tables |
| 7 | Downstream evidence separated correctly | PASS | Oracle, real audio and Sahara Sample A reconciled separately |
| 8 | Model strengths/limitations present | PASS | PDF findings and limitations section |
| 9 | Data, counts and preprocessing documented | PASS | Frozen manifest, report and evidence ledger |
| 10 | Ethics/Inclusion note present | PASS | `ETHICS_INCLUSION.md` |
| 11 | Demo <=5 minutes | IN PROGRESS | 3:05 script ready; rendered video must be timed |
| 12 | Public links accessible signed out | BLOCKED | Owner must insert and test demo/repository URLs |
| 13 | No secrets exposed | PASS | Environment-only API key; private audio/results ignored |
| 14 | No unsupported claims | PASS | Subset limitation, Yoruba weakness, empty result and unavailable Sahara latency disclosed |
| 15 | One-submission-only review | BLOCKED | Final Echo + Owner approval required immediately before submission |

## Final owner actions

1. Record and export the demo using `DEMO_SCRIPT.md`; confirm runtime <=5:00.
2. Upload the demo public/unlisted and test it while signed out.
3. Confirm the repository is public/accessibly shared and test it signed out.
4. Insert both URLs into `SUBMISSION_FORM_DRAFT.md` and the competition portal.
5. Open the benchmark PDF and confirm it contains exactly three pages.
6. Verify every portal number against the frozen comparison table.
7. Confirm no private audio, raw Sahara bundle, environment file or credential is public.
8. Echo and Owner perform the final review, then Owner makes the single submission.

## Stop rule

Smartie must not submit the entry. Owner retains final submission authority.