# Frozen AfriSwitch comparison — split-execution checkpoint

Sahara, Whisper Large-v3 and Whisper Small multilingual have completed the exact
frozen 20-sample comparison. Sahara latency fields remain empty because the API
evidence did not expose processing time; they must not be presented as zero.

All metric rows are corpus-weighted and derived from committed raw sample
results. Sahara's final empty transcript remains in the denominator. The local
preflight dependency failure is retained separately and is not included.
