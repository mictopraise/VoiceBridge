# Sahara CodeSwitch Africa Challenge - Submission Form Text

Status: final draft; placeholders require Owner input. Do not submit until the audit is green.

## Title

**VoiceBridge - From African Voice Notes to Business Action**

## Category

**Fintech, Telco & Customer Experience** - customer experience / agent assist for African micro and small businesses.

## Problem

African small businesses increasingly receive customer requests as voice notes mixing English, Nigerian Pidgin and local languages. Products, quantities, payment claims, locations and delivery instructions can be misunderstood or lost. Transcription alone still leaves the owner to interpret the request and decide what business action is safe.

## Target users

VoiceBridge serves African micro and small businesses, social-commerce sellers, retailers, service providers, delivery-oriented businesses and small support teams handling multilingual, voice-first customer communication.

## Solution

VoiceBridge converts a code-switched voice note into an editable transcript and a structured Action Card containing intent, customer request, product/service, quantity, amount, location, date/time, required action, missing information, confirmation flags and a concise editable reply. Its Never-Guess layer prevents uncertain critical details from silently becoming business instructions.

## Code-switching

**YES.** Demonstrated with real Pidgin-English and Yoruba-English Owner recordings and evaluated on a frozen AfriSwitch subset.

## Sahara API usage

**YES.** Intron Sahara processed the real flagship Pidgin-English Sample A and the frozen 20-sample AfriSwitch benchmark. LLM corrections were disabled for benchmark fairness. The exact Sahara model/version was not exposed by the API.

## Agentic / downstream capability

VoiceBridge does not stop at transcription. Its provider-independent Action Engine classifies one of 12 business intents, extracts operational entities, identifies missing or risky information, selects the required next action and generates a safe editable response. Critical values such as money, delivery location and payment claims can pause action until a human confirms them.

## Architecture choices and tradeoffs

A provider-neutral `ASRResult` contract separates speech recognition from business reasoning. Connected Sahara and local faster-whisper feed the same Action Engine, while benchmark mode records provider failure and never silently falls back. Sahara offers African-focused recognition but depends on network access and quota; local Whisper supports degraded connectivity but requires device storage and CPU time. Deterministic, inspectable extraction improves auditability for supported customer workflows but is less flexible than an open-ended chatbot. Categorical confidence is a conservative safety policy, not a calibrated probability.

## Ethics and inclusion

Owner recordings have explicit competition-demo consent; raw private audio is excluded from the public repository. AfriSwitch was used under granted access conditions. No credentials are committed. The subset was selected before model results; failures remain visible. Critical values require confirmation and payment claims require independent verification. All three models struggled on Yoruba-English, and VoiceBridge makes no claim of equal accuracy across languages, accents or devices.

## Evidence summary

On the frozen 20-sample AfriSwitch subset (10 Yoruba-English, 10 Pidgin-English), Sahara achieved 52.36% WER, Large-v3 61.08% and Whisper Small 84.29%. Sahara produced one terminal empty transcript and exposed no latency. Separately, the 13-case CSBiz oracle regression scored 100% on its authored fields; this is a transcript-level logic result, not ASR accuracy. Three real Owner recordings provide a small end-to-end proof and reveal meaningful ASR-conditioned safety failures.

## Links and attachments

- Demo video URL: **[OWNER TO INSERT PUBLIC/UNLISTED URL]**
- Code/documentation URL: **[OWNER TO INSERT PUBLIC REPOSITORY URL]**
- Benchmark report PDF: `output/pdf/VoiceBridge_Benchmark_Report.pdf`
- Ethics/Inclusion note: `ETHICS_INCLUSION.md`
- Optional benchmark audio: attach only within granted access and consent scope