# Action Card audit — 50 saved field interactions

Audit source: the owner's private 50-interaction JSON export reviewed locally.
The source file was not copied into the repository and no historical record was
modified.

## What the saved evidence can support

The export contains 50 genuine interaction records. Human review marked Action Card
usefulness as:

| Human rating | Count |
| --- | ---: |
| Yes | 3 |
| Partial | 5 |
| No | 42 |

The aggregate `critical_fields_correct` rating was:

| Human rating | Count |
| --- | ---: |
| Yes | 19 |
| Partial | 19 |
| No | 12 |

These figures are preserved observations, not post-fix results.

## Requested field-level audit

| Action Card field | Result from the 50-record export |
| --- | --- |
| Useful intent | Not measurable |
| Correct product/service | Not measurable |
| Correct quantity | Not measurable |
| Correct amount | Not measurable |
| Correct location | Not measurable |
| Correct date/time | Not measurable |
| Correct required action | Not measurable |

The export does not persist the Action Card payload or separate field-level truth and
correctness labels. Only 5 of 50 records retain a working transcript, 1 retains a
human-reference meaning, none retains verified critical information, and no record
contains the generated structured Action Card. The aggregate critical-field rating
cannot honestly be decomposed into product, quantity, amount, location, or date/time.
The human-entered `use_case` is not sufficient to score generated intent because the
generated intent itself was not retained.

## Finding

The audit confirms that the earlier logger can describe perceived usefulness and
aggregate critical-field correctness, but it cannot reproduce field-level Action Card
accuracy. Historical results must not be reconstructed or rewritten. Future reviews
should retain a sanitized structured Action Card snapshot or explicit per-field human
labels when consent and privacy rules permit.
