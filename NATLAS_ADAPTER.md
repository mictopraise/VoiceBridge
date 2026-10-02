# N-ATLAS local ASR adapter

Phase 2B adds a provider-neutral local adapter for the official NCAIR model
repositories. It does not change the browser workflow or make N-ATLAS the
product default; that integration belongs to Phase 2C.

## Supported selections

| Selected language | Official repository |
| --- | --- |
| `yo` | `NCAIR1/Yoruba-ASR` |
| `en-NG` | `NCAIR1/NigerianAccentedEnglish` |

No Nigerian Pidgin model is claimed. Hausa and Igbo are intentionally outside
the initial Phase 2B mapping.

## Runtime contract

1. VoiceBridge preprocessing supplies mono, 16 kHz, 16-bit PCM WAV.
2. The caller explicitly selects `yo` or `en-NG`; the adapter does not claim
   automatic language detection.
3. The selected official model is loaded lazily through the local Transformers
   pipeline. One model is retained at a time and reused for later calls with
   the same selection.
4. The transcript is returned through the existing `ASRResult` contract.
5. Confidence, segments, and timestamps remain unavailable rather than being
   invented.

Audio over 30 seconds raises a controlled error before model loading. It is not
truncated, and chunking is not implemented in this phase. Provider failures do
not invoke Whisper inside the adapter.

N-ATLAS performs transcription only. Any English-meaning/translation stage and
any user correction must retain separate provenance.

## Optional local dependencies

Install the additional local N-ATLAS runtime with:

```text
python -m pip install -r requirements-natlas.txt
```

The optional file uses the official PyTorch CPU wheel index to avoid an
accidental multi-gigabyte CUDA installation on CPU systems. Hugging Face access
must be configured locally under the official repository terms. Tokens and
downloaded model files must never be committed.

The live Yoruba acceptance test established `torch==2.6.0+cpu` as the compatible
CPU runtime for the installed Transformers range. PyTorch 2.4.1 failed the
current Transformers security/runtime check and is intentionally not supported
by this build; the check is not bypassed or weakened.

## Controlled Yoruba acceptance test

After authenticating with Hugging Face locally and accepting the official model
terms, run the repository-owned acceptance command from the project root:

```text
python -m scripts.run_natlas_acceptance --audio "C:\path\to\short-yoruba.wav"
```

The runner calls `NAtlasEngine`; it does not invoke a standalone ASR path. It
writes a redacted local JSON record under `benchmark/naic/live_acceptance/`,
which is excluded from Git by default. It never accepts or prints a token.
