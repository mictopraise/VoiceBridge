# Public Release Note

This package is derived from the VoiceBridge competition build at milestone `a45012c`.

For public distribution, gated AfriSwitch reference-bearing files and raw per-sample ASR outputs have been intentionally omitted. The public package retains aggregate benchmark summaries, methodology, code, architecture, tests, ethics/safety documentation, and the final benchmark PDF.

Omitted from this public release:
- `benchmark/afriswitch/owner_pinned_manifest.jsonl`
- AfriSwitch `raw_results.jsonl` files containing reference transcripts and per-sample outputs

These omissions protect dataset-access/licensing boundaries and do not change the frozen aggregate results reported in the competition benchmark. No private audio, API credentials, populated `.env` files, or provider secrets are included.