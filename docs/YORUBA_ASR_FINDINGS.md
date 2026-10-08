# Yoruba ASR Findings from Real-World Validation

## Scope

This note records qualitative findings from VoiceBridge product testing and an
external 20-item Yoruba transcription assessment. It does not reproduce private
participant recordings, participant identifiers, proprietary assessment items,
reference answers, or restricted source material.

These findings describe observed limitations. They do **not** establish that
VoiceBridge currently solves Yoruba or Yoruba code-switch speech recognition.

## Observations

### Model execution success is not transcription accuracy

An ASR provider can accept an audio file, finish inference, and return a
well-formed transcript while the text remains inaccurate. VoiceBridge testing
showed that N-ATLAS Yoruba can produce fluent-looking Yoruba that does not
faithfully represent the spoken audio. A successful provider response must
therefore be recorded as *processing success*, not automatically as *ASR Pass*.

VoiceBridge keeps these judgments separate:

- provider processing outcome;
- ASR Pass / Partial / Fail;
- semantic meaning Yes / Partial / No;
- critical business-field accuracy;
- Action Card usefulness; and
- task completion.

The latter five require human review.

### Fluent but wrong output is a material risk

Grammatical or natural-looking Yoruba can create false confidence. During
testing, some output appeared linguistically plausible even when its words or
meaning did not align with the recording. This failure mode is more dangerous
than an obvious empty or broken transcript because a reviewer may assume fluency
means fidelity.

VoiceBridge must not treat fluency, provider completion, or the presence of
diacritics as proof that a transcript is correct.

### Code-switch performance is asymmetric

Anonymized VoiceBridge cases showed that Yoruba-English and Yoruba-Pidgin-English
recordings do not necessarily fail uniformly. For example:

- an English or Pidgin request marker could survive while the surrounding Yoruba
  content was altered or lost;
- a product, quantity, or delivery word in English could be preserved while a
  Yoruba qualifier or location phrase was unreliable; and
- a second provider could preserve a different span of the same utterance rather
  than simply being better or worse everywhere.

This means aggregate WER alone may hide which language span failed and whether
the error changed the business instruction.

### N-ATLAS confidence is unavailable

The current N-ATLAS integration does not receive calibrated provider confidence.
VoiceBridge therefore records provider confidence as **Not provided**. It must
not invent a percentage, convert successful execution into confidence, or imply
that its conservative safety state is provider-supplied probability.

### Exact-string scoring is insufficient on its own

The external 20-item Yoruba assessment showed that binary exact-match scoring
can combine several different phenomena into one incorrect result:

- Unicode representation differences;
- punctuation;
- spacing;
- capitalization;
- Yoruba diacritic differences; and
- genuine word, omission, insertion, or semantic errors.

Exact equality remains reproducible and may be reported, but it must not be the
sole evaluation. Raw orthographic accuracy and carefully documented normalized
variants should be shown separately. Normalization must never be used to hide a
genuine lexical or meaning-changing error.

## Human confirmation requirement

Human review remains mandatory for consequential use. Reviewers should listen to
the recording while checking:

- the original immutable provider transcript;
- the editable working transcript;
- the separately attributed English meaning;
- the actual language mixture;
- amounts, quantities, locations, dates, times, order references and payment
  claims; and
- any unsupported or fluent-but-wrong content.

Payment speech is a customer claim, not independent proof of payment. Uncertain
critical fields must remain unknown or require confirmation under Never-Guess.

## VoiceBridge risk controls

Real-world testing supports retaining the existing controls:

- immutable provider transcript;
- editable working transcript without overwriting the raw output;
- separate translation/English-meaning provenance;
- exact provider and model provenance;
- Never-Guess handling for critical business fields;
- visible human confirmation;
- separate field-test scores; and
- preservation of partial and failed results as evidence.

These controls mitigate risk; they do not repair an inaccurate ASR transcript.

## Current limitations

- The present evidence set is too small for population-level claims.
- Speaker, accent, dialect, device and noise coverage remain limited.
- The current system does not automatically identify trustworthy code-switch
  spans.
- N-ATLAS does not expose calibrated confidence through the current local model
  integration.
- Diacritic-insensitive scoring can improve comparability but cannot replace
  strict Yoruba orthographic evaluation.
- Semantic review depends on qualified human judgment and clear annotation
  guidance.
- VoiceBridge does not currently solve Yoruba code-switch ASR.

## Research questions

1. Which Yoruba, English and Pidgin spans are consistently preserved or lost by
   each provider?
2. How should code-switch boundaries be annotated when a token could reasonably
   belong to more than one language?
3. Which normalization steps improve evaluation fairness without concealing
   diacritic or lexical errors?
4. Can unsupported-content detection identify fluent but acoustically ungrounded
   Yoruba output?
5. Which errors most often corrupt money, quantity, location, date/time, product,
   payment status and order references?
6. How much human correction is required before an Action Card becomes safe and
   useful?
7. What speaker, dialect, device and noise coverage is needed for a defensible
   Nigerian code-switch benchmark?
8. When is provider comparison useful, and when do multiple providers repeat the
   same failure?

See [ASR_EVALUATION_STANDARD.md](ASR_EVALUATION_STANDARD.md) for the proposed
measurement framework.
