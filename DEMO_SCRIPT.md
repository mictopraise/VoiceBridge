# VoiceBridge Competition Demo Script and Shot List

Target runtime: **3:05**. Absolute limit: **5:00**. Use Sample A under the Owner's granted competition-demo consent. Do not expose raw private file paths, credentials or unsupported provider metadata.

| Time | Screen / action | Narration |
| --- | --- | --- |
| 0:00-0:18 | Title over WhatsApp-style voice-note visual | "African small businesses receive customer requests as voice notes that naturally mix Pidgin, Yoruba and English. A transcript alone still leaves the owner to decide what the customer wants and what is safe to do." |
| 0:18-0:35 | VoiceBridge upload screen and compact pipeline | "VoiceBridge turns code-switched speech into structured business action: transcript, intent, entities, missing details, a required next step and an editable reply." |
| 0:35-0:55 | Play real Sample A; label: Owner recording, Tecno Spark 9T | "This real Pidgin-English message requests two black Bluetooth headphones, delivery to Mokola tomorrow afternoon, the total price and an urgent response." |
| 0:55-1:27 | Show saved Sahara transcript, then Action Card | "Sahara preserved the request, quantity, product, colour, delivery timing and cost enquiry. VoiceBridge classifies DELIVERY_REQUEST and structures the product, quantity, location, date, time and next action. Mokola was transcribed as Mocola, and ASAP as 'as', so the output stays editable." |
| 1:27-1:52 | Show confirmation banner using Sample B or controlled ambiguous amount example | "VoiceBridge does not treat every recognized word as safe business data. When a critical field is missing or ambiguous, Never-Guess marks it for confirmation, changes the required action and prevents the reply from asserting it as fact." |
| 1:52-2:22 | Display frozen AfriSwitch comparison table | "On our frozen 20-sample AfriSwitch subset, Sahara recorded 52.36 percent WER, Large-v3 61.08 and Whisper Small 84.29. Sahara led on Pidgin-English. All three struggled on Yoruba-English, and Sahara produced one terminal empty transcript. These are subset-specific results, not universal claims." |
| 2:22-2:50 | Architecture graphic or repository modules | "The speech engines are replaceable. VoiceBridge owns the normalized provider layer, 12-intent taxonomy, entity extraction, missing-information logic, Never-Guess safety, Action Card, safe reply generation, local Whisper fallback and downstream benchmark." |
| 2:50-3:05 | Closing card and tagline | "If Sahara disappeared, the business-action and safety engineering would remain. VoiceBridge: from African voice notes to business action." |

## Capture checklist

- Use the saved Sample A Sahara result; do not make another API request.
- Show `Intron Sahara - exact model/version not exposed by API`.
- Keep the terminal failure visible in the table.
- Do not claim Sahara latency; mark it unavailable.
- Do not merge AfriSwitch ASR metrics with CSBiz downstream scores.
- Show at least one visible code-switch example and one confirmation state.
- Keep benchmark discussion under 40 seconds; product value is primary.
- Export at 1080p, verify audio intelligibility and keep final runtime below 5:00.
- Upload as public or unlisted, then test the URL in a signed-out browser.