# VoiceBridge Evidence Ledger

This ledger distinguishes saved provider evidence, measured results and unavailable
metadata. Private source files remain excluded from Git.

## M3 — Sahara Sample A

| Field | Evidence |
| --- | --- |
| Provider | Intron Sahara |
| Exact model/version | Not exposed by saved API response; documentation review required |
| Sample | `flagship_a` / `csbiz_flagship_A.wav` |
| Final status | `FILE_TRANSCRIBED` |
| Provider file ID | `38292b63-bdd0-490d-8e67-6b309505b243` |
| Language setting | `pcm` |
| LLM correction | Disabled |
| Audio SHA-256 | `ad24f8cede344b1719567e9be019b6b90df399c5124884f12b1fccfe0ec4e663` |
| Upload response SHA-256 | `5890b09af299182d08797f789275f879afb87c771da2c5d89e6ff191c94d1472` |
| Final-status response SHA-256 | `535cf7f3dbd051e424b30ce3ceb2439a94d9db2e73d99116681b32ee28df211e` |
| Cache identity | `9fd7e01959c2bea641aa1166baf35214174251439985911147230d378af25ead` |
| Provider duration | 16 seconds |
| Provider processing latency | Not exposed in saved responses |
| API calls made by M3 integration | 0 |

### Frozen reference

> Abeg I wan order two Bluetooth headphones, the black ones. I need am delivered
> to Mokola tomorrow afternoon. How much everything go cost? Thank you. I need
> your response ASAP.

### Saved Sahara transcript, uncorrected

> Abeg I wan order 2 blue tooth headphones the black ones I need am deliver to
> Mocola tomorrow afternoon How much everything go cost Thank you I need your
> response as

### Measured results

| WER | CER | Strict WER | Strict CER | Intent | Entity | Critical entity | Business action | Never-Guess |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20.00% | 5.71% | 36.67% | 9.59% | 100.00% | 60.00% | 75.00% | 50.00% | 0.00% |

Sahara preserved the Pidgin-English request, quantity, black variant, date, time
and price enquiry. `Bluetooth` became `blue tooth`, `Mokola` became `Mocola`, and
`ASAP` became `as`. The intent remained `DELIVERY_REQUEST`; product specificity
and location did not exactly match the reference.

No provider confidence was exposed. VoiceBridge did not invent one: the frozen
Action Engine conservatively marked extracted critical fields low-confidence,
changing the required action and producing a false-positive confirmation. This
explains the 0% Never-Guess result for this clear-reference case.