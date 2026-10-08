# VoiceBridge ASR Evaluation Standard

## Purpose

This standard defines how future VoiceBridge speech experiments should separate
orthographic, lexical, semantic and business-critical performance. It applies to
provider and model comparisons on the same frozen audio/reference set.

**Exact-string equality must not be the sole evaluation metric.** It may be
reported as one strict indicator, but every conclusion must consider the metric
family below and the actual use case.

## Reference and provenance requirements

Each evaluated sample should record, where lawfully available:

- stable sample ID and dataset/source;
- consent or dataset licence status;
- raw human reference transcript;
- language or language mix;
- provider and exact model identity;
- raw provider hypothesis;
- documented normalization outputs;
- provider failure state;
- human semantic and critical-field review; and
- scorer/version identity.

Never silently rewrite the authoritative human reference. Store transformed
references and hypotheses as derived evaluation artifacts.

## Metric suite

### A. Raw Word Error Rate (WER)

Compute substitutions, deletions and insertions on the raw tokenized reference
and hypothesis. Preserve the documented source orthography, including Yoruba
diacritics. Report corpus-weighted and sample-level results.

### B. Raw Character Error Rate (CER)

Compute character edit distance on the raw reference and hypothesis. CER helps
surface spelling and diacritic differences that word tokenization can obscure.

### C. Unicode-normalized WER/CER

Normalize both strings to one explicitly documented Unicode form, preferably
NFC, then apply only general transparent rules such as consistent whitespace.
Report this beside, not instead of, the raw score. Do not strip Yoruba diacritics
in this metric.

### D. Diacritic-insensitive WER/CER

Create a separate diagnostic view by decomposing Unicode characters and removing
combining marks consistently from both reference and hypothesis. Label it
**diacritic-insensitive**. Never describe it as full Yoruba orthographic accuracy.

The gap between Unicode-normalized and diacritic-insensitive results estimates
the contribution of diacritic errors; it does not excuse lexical errors.

### E. Yoruba-token accuracy

Using human-reviewed language-span labels, score Yoruba reference tokens
correctly preserved by the hypothesis. Report correct Yoruba tokens divided by
applicable Yoruba reference tokens, with token alignment rules documented.

### F. English/Pidgin-token accuracy

Using the same alignment and human-reviewed span labels, score English and
Nigerian Pidgin tokens separately where annotation supports that distinction.
If English/Pidgin separation is ambiguous, report the combined category and state
the limitation.

### G. Code-switch boundary accuracy

Compare human-annotated switch points with predicted/preserved language-span
transitions. A boundary should receive credit only within a predefined tolerance,
such as the adjacent token position. Report precision, recall and F1 where the
dataset supports reliable boundary annotation.

Do not infer boundary accuracy solely from provider-level language selection.

### H. Semantic meaning

Human reviewers assign:

- **Yes** — intended meaning is preserved;
- **Partial** — the main request survives but relevant meaning is missing,
  uncertain or altered; or
- **No** — core meaning is lost or reversed.

Provide annotation guidance and adjudicate disagreements for formal reporting.

### I. Critical business-field accuracy

Evaluate only applicable reference fields:

- product or service;
- quantity;
- amount;
- location/address;
- date and time;
- order/payment reference; and
- payment status or claim.

Score exact or normalized field agreement according to field-specific rules.
Meaning-changing number, polarity or payment errors must remain visible even when
overall WER is acceptable.

### J. Hallucination / unsupported-content indicator

Human reviewers mark whether the hypothesis contains material words or claims
that are not supported by the audio. Track at least:

- none;
- minor unsupported content; and
- material unsupported content.

Fluent grammatical output can still be unsupported. An empty transcript is a
provider failure, not a hallucination.

### K. Human correction distance

Measure the edit distance from raw provider transcript to the human-corrected
working transcript. Report word- and character-level distance plus the human
correction category already used by VoiceBridge:

- none;
- minor; or
- major.

This measures correction effort; it is not a replacement for reference-based
accuracy.

### L. Model/provider comparison

Run providers on the same frozen samples and references with identical scoring
code and failure accounting. Record:

- attempted, successful and failed samples;
- exact provider/model identity;
- language configuration;
- raw and normalized metrics;
- semantic and critical-field results;
- unsupported-content rate;
- correction effort; and
- latency/RTF only when genuinely measured and comparable.

Do not silently retry, substitute a provider, remove failures, or compare models
on different samples without prominent disclosure.

## Error taxonomy

Every reviewed error may carry one or more labels:

| Category | Meaning |
| --- | --- |
| Acoustic/lexical | Spoken word omitted, inserted or replaced |
| Diacritic | Yoruba base letters broadly preserved but tone/underdot marks differ |
| Orthographic/normalization | Unicode, spacing, case or punctuation difference without a lexical change |
| Semantic | Intended meaning altered, lost or reversed |
| Critical business field | Product, number, money, location, time, reference or payment claim corrupted |
| Unsupported content | Material content appears without support in the audio |

Categories may overlap. For example, one lexical substitution can also be a
semantic and critical-business-field error.

## Reporting rules

- Publish strict and normalized results with unambiguous labels.
- Document every transformation before scoring.
- Retain provider failures in denominators and qualitative findings.
- Separate provider processing success from ASR accuracy.
- State sample size, language mix and selection procedure.
- Avoid universal model claims from small or narrow subsets.
- Preserve failed and partial outputs as real validation evidence.
- Keep ASR metrics separate from downstream Action Card metrics.
