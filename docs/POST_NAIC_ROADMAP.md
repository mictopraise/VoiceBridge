# VoiceBridge Post-NAIC Roadmap

## Workstream: VoiceBridge ASR Lab

### Objective

Develop an evaluation and adaptation layer for real Nigerian speech, with an
initial research focus on Yoruba, Nigerian-accented English, Nigerian Pidgin and
their natural code-switching. The lab should improve measurement and safe model
selection before considering model adaptation.

This roadmap describes future work. It must not be presented as functionality
already delivered in the NAIC build.

## Proposed pipeline

```text
Audio
  → language/span analysis
  → ASR provider/model
  → uncertainty/error detection
  → transcript comparison
  → human verification
  → business Action Card
  → evaluation dataset
  → future model adaptation
```

The immutable raw provider transcript and provider/model provenance remain the
audit baseline throughout the pipeline.

## Phase 1 — Evaluation specification

- Implement the metric suite in
  [ASR_EVALUATION_STANDARD.md](ASR_EVALUATION_STANDARD.md).
- Define Yoruba, English and Pidgin span-annotation guidance.
- Define hallucination/unsupported-content and correction-effort labels.
- Establish reviewer training and disagreement adjudication.
- Version normalization and scoring code.

## Phase 2 — VoiceBridge-ASR-Benchmark-v1

Create a frozen, reproducible benchmark containing:

- clean and noisy recordings;
- different speakers, devices and environments;
- Yoruba-only, Nigerian-English-only, Pidgin-English and Yoruba-English/Pidgin
  code-switch cases;
- business and non-business speech partitions;
- raw references, language spans and critical-field annotations where
  applicable; and
- explicit source, consent, licence and permitted-use metadata.

The benchmark may use only:

- owner-collected recordings with suitable participant consent for the stated
  evaluation or training purpose;
- properly licensed public datasets; and
- data explicitly permitted for research or model training.

CrowdGen/Appen or other proprietary assessment content must not enter the
repository, benchmark, publication or training set unless written licence or
permission has been verified. Completing or viewing an assessment does not grant
dataset reuse rights.

## Phase 3 — Cross-provider error analysis

- Run each approved provider on the same frozen samples.
- Preserve failures and empty transcripts.
- Compare language spans rather than only aggregate WER.
- Identify fluent-but-wrong and unsupported-content patterns.
- Measure critical business-field corruption and human correction effort.
- Document deployment, latency and hardware trade-offs only from measured data.

## Phase 4 — Uncertainty and error detection

Research signals that do not pretend to be provider confidence, including:

- disagreement between independent providers;
- unstable critical fields across repeated or alternative runs;
- transcript/audio length anomalies;
- language-span inconsistency;
- unsupported-content indicators;
- number, money and payment-claim conflicts; and
- human correction patterns.

Any derived score must be labelled as a VoiceBridge policy or diagnostic signal,
not calibrated provider probability unless calibration is demonstrated.

## Phase 5 — Adaptation decision gate

Only consider fine-tuning, adapters, language-model rescoring or other model
adaptation after:

1. data rights and consent are verified;
2. a reproducible baseline is frozen;
3. error patterns justify the intervention;
4. a held-out evaluation set exists; and
5. compute, privacy and maintenance costs are understood.

Training data and evaluation data must remain separated. Improvements must be
reported against the frozen held-out set without sample removal or cherry-picking.

## Product feedback loop

Field-test findings should continue to inform product safety:

- immutable provider transcript;
- editable working transcript;
- separately attributed English meaning;
- Never-Guess confirmation for critical fields;
- provider/model provenance;
- human semantic and business-field review; and
- retention of partial and failed outputs.

The ASR Lab complements these controls. It does not remove the need for human
confirmation in consequential business actions.

## NAIC positioning

Real-world validation revealed a genuine limitation: Yoruba and Yoruba-mixed
speech may be transcribed unreliably, including fluent-looking but incorrect
output. VoiceBridge does not claim to have solved this problem. Its present
contribution is an auditable, provider-neutral workflow that exposes provenance,
keeps raw and corrected text separate, applies Never-Guess safeguards and
collects structured human evaluation. The limitation defines a credible future
adaptation opportunity for VoiceBridge ASR Lab.
