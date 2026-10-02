"""Run one secure, local, end-to-end N-ATLAS Yoruba acceptance test."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable
import wave

from speech_engines.base import EmptyTranscriptError, ProviderUnavailableError
from speech_engines.natlas_engine import (
    NAtlasAccessError,
    NAtlasAudioFormatError,
    NAtlasAudioTooLongError,
    NAtlasEngine,
    NAtlasInferenceError,
    NAtlasResponseError,
    NAtlasTaskError,
    OFFICIAL_MODELS,
    transformers_pipeline_factory,
)


DEFAULT_OUTPUT = Path("benchmark/naic/live_acceptance/natlas_yoruba_acceptance.json")
SECRET_PATTERN = re.compile(r"(?i)(?:hf_[a-z0-9]{16,}|bearer\s+[a-z0-9._-]{16,})")


def redact(value: str) -> str:
    return SECRET_PATTERN.sub("[REDACTED]", value)


def bytes_in_tree(path: Path) -> int | None:
    if not path.is_dir():
        return None
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
    except OSError:
        return None
    return total


def official_cache_path(model_id: str, cache_root: Path | None = None) -> Path:
    if cache_root is None:
        try:
            from huggingface_hub.constants import HF_HUB_CACHE
        except ImportError:
            return Path(".unavailable-huggingface-cache")
        cache_root = Path(HF_HUB_CACHE)
    return cache_root / f"models--{model_id.replace('/', '--')}"


def process_observation() -> dict[str, Any]:
    observation: dict[str, Any] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "processor": platform.processor() or None,
        "logical_cpu_count": os.cpu_count(),
        "process_rss_bytes": None,
        "system_ram_total_bytes": None,
        "system_ram_available_bytes": None,
    }
    try:
        import psutil
        process = psutil.Process()
        memory = psutil.virtual_memory()
        observation.update({
            "process_rss_bytes": process.memory_info().rss,
            "system_ram_total_bytes": memory.total,
            "system_ram_available_bytes": memory.available,
        })
    except (ImportError, OSError):
        pass
    return observation


def wav_observation(audio_path: Path) -> dict[str, Any]:
    with wave.open(str(audio_path), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate()
        return {
            "filename": audio_path.name,
            "duration_seconds": frames / rate if rate else 0.0,
            "sample_rate_hz": rate,
            "channels": handle.getnchannels(),
            "sample_width_bytes": handle.getsampwidth(),
            "format": "PCM WAV",
        }


def model_revision(model_pipeline: Any) -> str | None:
    model = getattr(model_pipeline, "model", None)
    config = getattr(model, "config", None)
    revision = getattr(config, "_commit_hash", None)
    return str(revision) if revision else None


def model_parameter_bytes(model_pipeline: Any) -> int | None:
    model = getattr(model_pipeline, "model", None)
    parameters = getattr(model, "parameters", None)
    if not callable(parameters):
        return None
    try:
        return sum(parameter.numel() * parameter.element_size() for parameter in parameters())
    except (AttributeError, RuntimeError, TypeError):
        return None


def classify_failure(exc: Exception) -> str:
    if isinstance(exc, NAtlasAccessError):
        return "access"
    if isinstance(exc, NAtlasAudioFormatError):
        return "audio-input issue"
    if isinstance(exc, (wave.Error, EOFError, FileNotFoundError)):
        return "audio-input issue"
    if isinstance(exc, NAtlasAudioTooLongError):
        return "audio-input issue"
    if isinstance(exc, NAtlasInferenceError):
        return "inference"
    if isinstance(exc, (NAtlasResponseError, EmptyTranscriptError)):
        return "inference"
    if isinstance(exc, ProviderUnavailableError):
        return "dependency/download/compatibility"
    if isinstance(exc, MemoryError):
        return "memory"
    if isinstance(exc, NAtlasTaskError):
        return "compatibility"
    return "compatibility"


def run_acceptance(
    audio_path: str | Path,
    *,
    output_path: str | Path = DEFAULT_OUTPUT,
    pipeline_loader: Callable[[str, int | str], Any] = transformers_pipeline_factory,
    observation_probe: Callable[[], dict[str, Any]] = process_observation,
    cache_root: Path | None = None,
) -> dict[str, Any]:
    audio = Path(audio_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    model_id = OFFICIAL_MODELS["yo"]
    cache_path = official_cache_path(model_id, cache_root)
    cache_existed_before = cache_path.is_dir()
    cache_bytes_before = bytes_in_tree(cache_path)
    timing: dict[str, float | None] = {"model_load_seconds": None}
    observations = {"before": observation_probe()}
    loaded_pipeline: dict[str, Any] = {}

    def measured_loader(requested_model: str, device: int | str):
        started = perf_counter()
        pipeline = pipeline_loader(requested_model, device)
        timing["model_load_seconds"] = perf_counter() - started
        loaded_pipeline["value"] = pipeline
        observations["after_model_load"] = observation_probe()
        return pipeline

    started_total = perf_counter()
    try:
        audio_details = wav_observation(audio)
        engine = NAtlasEngine(pipeline_factory=measured_loader, device=-1)
        result = engine.transcribe(str(audio), language="yo", task="transcribe")
        total_seconds = perf_counter() - started_total
        observations["after_inference"] = observation_probe()
        cache_bytes_after = bytes_in_tree(cache_path)
        report = {
            "schema": "voicebridge.natlas.acceptance.v1",
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "SUCCESS",
            "model": {
                "official_repository": model_id,
                "revision": model_revision(loaded_pipeline.get("value")),
                "selected_language": "yo",
                "language_selection": "explicit",
                "cache_existed_before": cache_existed_before,
                "load_outcome": "loaded_successfully",
                "cache_bytes_before": cache_bytes_before,
                "cache_bytes_after": cache_bytes_after,
                "official_repository_cache_bytes": cache_bytes_after,
                "inference_model_parameter_bytes": model_parameter_bytes(
                    loaded_pipeline.get("value")
                ),
                "footprint_note": (
                    "Parameter bytes measure loaded model tensors only; repository cache bytes "
                    "include model configuration and processor/tokenizer assets."
                ),
            },
            "audio": audio_details,
            "timing": {
                "model_load_seconds": timing["model_load_seconds"],
                "inference_seconds": result.processing_seconds,
                "total_voicebridge_seconds": total_seconds,
                "timing_source": "VoiceBridge wall clock",
            },
            "runtime": {
                "device": "cpu",
                "observations": observations,
            },
            "transcript": result.transcript,
            "asr_result": result.to_dict(),
            "assertions": {
                "used_natlas_engine": result.engine == "natlas",
                "exact_model_identity": result.model == model_id,
                "confidence_unavailable": result.metadata.get("confidence") is None,
                "segments_unavailable": result.segments == [],
                "timestamps_unavailable": result.metadata.get("timestamps_available") is False,
                "no_whisper_fallback": result.engine == "natlas",
                "no_translation": result.metadata.get("translation_performed") is False,
                "no_chunking_or_truncation": audio_details["duration_seconds"] <= 30.0,
            },
        }
    except Exception as exc:
        report = {
            "schema": "voicebridge.natlas.acceptance.v1",
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "FAILED",
            "model": {"official_repository": model_id, "selected_language": "yo"},
            "audio": {"filename": audio.name},
            "failure": {
                "classification": classify_failure(exc),
                "exception_type": type(exc).__name__,
                "message": redact(str(exc)),
            },
            "timing": {**timing, "total_voicebridge_seconds": perf_counter() - started_total},
            "runtime": {"device": "cpu", "observations": observations},
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one local official N-ATLAS Yoruba acceptance test through NAtlasEngine."
    )
    parser.add_argument("--audio", required=True, help="Short normalized Yoruba WAV file")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Redacted local JSON output")
    args = parser.parse_args()
    report = run_acceptance(args.audio, output_path=args.output)
    print(f"Status: {report['status']}")
    print(f"Evidence: {Path(args.output).resolve()}")
    if report["status"] == "SUCCESS":
        print(f"Model: {report['model']['official_repository']}")
        print(f"Revision: {report['model']['revision'] or 'not exposed by loaded config'}")
        print(f"Transcript: {report['transcript']}")
        raise SystemExit(0)
    failure = report["failure"]
    print(f"Failure class: {failure['classification']}")
    print(f"Failure: {failure['exception_type']}: {failure['message']}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
