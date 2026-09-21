# VoiceBridge Ethics and Inclusion Note

VoiceBridge is designed for African micro and small businesses whose customers communicate naturally through multilingual voice notes. It treats accents and code-switching as normal communication, not user error.

- Obtain informed consent before using recordings for evaluation, demonstration or publication.
- The three Owner recordings have explicit consent for competition-demo playback, transcript display and product-output display.
- Keep private customer audio out of the public repository unless the speaker explicitly permits release.
- Raw Owner recordings remain excluded from the public repository despite the limited demo consent.
- Label synthetic speech and human speech separately.
- Use AfriSwitch only under the Owner's granted access and licence conditions.
- Preserve the deterministic pre-result sample selection; do not cherry-pick or replace difficult samples.
- Preserve Yoruba diacritics and disclose normalization choices.
- Report unsupported languages, failed runs and low confidence instead of silently excluding them.
- Keep Sahara's terminal empty transcript in the benchmark denominator and raw evidence.
- Never invent amounts, quantities, addresses, dates, payment states or order references.
- Require human confirmation for uncertain critical fields and independent verification for customer-reported payments.
- Treat confidence categories as conservative product rules, not calibrated probabilities.
- Document limitations across accents, devices, background noise and language mixtures.
- Acknowledge that all three measured systems struggled on Yoruba-English and do not claim equal performance across languages.
- Keep credentials in excluded environment variables and never print or commit them.
- Provide local Whisper processing as a future degraded-connectivity option while keeping the business workflow independent of the speech provider.

VoiceBridge assists customer operations; it does not authorize payments, confirm transactions or replace human business judgment.