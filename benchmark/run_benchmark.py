"""Run identical manifest samples through named ASR providers without fallback."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Callable

from action_engine import analyze_business_action
from speech_engines import create_engine
from speech_engines.base import SpeechEngineError

from .evaluate_actions import evaluate_action
from .manifest import load_manifest
from .metrics import speech_metrics

AVERAGE_METRICS = ("total_processing_seconds", "real_time_factor")


def _mean(rows: list[dict], field: str):
    values = [row[field] for row in rows if row.get(field) is not None]
    return mean(values) if values else None


def _ratio(rows: list[dict], numerator: str, denominator: str):
    numerator_total = sum(row.get(numerator, 0) for row in rows)
    denominator_total = sum(row.get(denominator, 0) for row in rows)
    return numerator_total / denominator_total if denominator_total else None


def summarize(rows: list[dict], group_fields: tuple[str, ...]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(field, "") for field in group_fields)].append(row)
    output = []
    for group, items in sorted(groups.items()):
        successful = [item for item in items if item["status"] == "succeeded"]
        summary = dict(zip(group_fields, group))
        summary.update({"attempted": len(items), "succeeded": len(successful), "failed": len(items)-len(successful)})
        summary.update({
            "wer": _ratio(successful, "word_errors", "reference_words"),
            "cer": _ratio(successful, "character_errors", "reference_characters"),
            "strict_wer": _ratio(successful, "strict_word_errors", "strict_reference_words"),
            "strict_cer": _ratio(successful, "strict_character_errors", "strict_reference_characters"),
            "intent_accuracy": _ratio(successful, "intent_correct", "intent_applicable"),
            "entity_accuracy": _ratio(successful, "entity_correct", "entity_applicable"),
            "business_action_accuracy": _ratio(successful, "business_action_correct", "business_action_applicable"),
            "critical_entity_accuracy": _ratio(successful, "critical_entity_correct", "critical_entity_applicable"),
            "never_guess_accuracy": _ratio(successful, "never_guess_correct", "never_guess_applicable"),
            "required_action_accuracy": _ratio(successful, "required_action_correct", "required_action_applicable"),
            "missing_information_accuracy": _ratio(successful, "missing_information_correct", "missing_information_applicable"),
        })
        summary.update({field: _mean(successful, field) for field in AVERAGE_METRICS})
        output.append(summary)
    return output


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_benchmark(manifest_path: str | Path, engine_names: list[str], output_dir: str | Path, *, model: str="large-v3", engine_factory: Callable[..., object]=create_engine) -> list[dict]:
    manifest_path = Path(manifest_path)
    samples = load_manifest(manifest_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    rows=[]
    for engine_name in engine_names:
        try:
            engine=engine_factory(engine_name,model=model); provider_error=None
        except Exception as exc:
            engine=None; provider_error=exc
        for sample in samples:
            base={"sample_id":sample["sample_id"],"dataset":sample.get("dataset",""),"language_pair":sample.get("language_pair",""),"engine":engine_name,"model":getattr(engine,"model",model)}
            audio_path=(manifest_path.parent/sample["audio_path"]).resolve()
            try:
                if provider_error: raise provider_error
                if not audio_path.is_file(): raise FileNotFoundError(f"Audio file not found: {sample['audio_path']}")
                asr=engine.transcribe(str(audio_path),language=sample.get("forced_language"))
                if not asr.transcript.strip(): raise ValueError("Engine returned an empty transcript.")
                started=perf_counter()
                action=analyze_business_action(asr.transcript,asr_language=asr.detected_language,asr_confidence=asr.metadata.get("confidence"))
                action_seconds=perf_counter()-started
                metrics=speech_metrics(sample["reference_transcript"],asr.transcript)
                downstream=evaluate_action(action,sample)
                total_seconds=asr.processing_seconds+action_seconds
                rows.append({**base,"status":"succeeded","reference_transcript":sample["reference_transcript"],"raw_transcript":asr.transcript,"normalized_asr":asr.to_dict(),"detected_language":asr.detected_language,**metrics,"action":action,**downstream,"audio_seconds":asr.audio_seconds,"asr_processing_seconds":asr.processing_seconds,"action_processing_seconds":action_seconds,"total_processing_seconds":total_seconds,"real_time_factor":total_seconds/asr.audio_seconds if asr.audio_seconds else None,"error_type":None,"error":None})
            except Exception as exc:
                rows.append({**base,"status":"failed","error_type":type(exc).__name__,"error":str(exc)})
    with (output_path/"raw_results.jsonl").open("w",encoding="utf-8") as handle:
        for row in rows: handle.write(json.dumps(row,ensure_ascii=False)+"\n")
    model_summary=summarize(rows,("engine","model"))
    language_summary=summarize(rows,("engine","model","dataset","language_pair"))
    downstream_summary=[{"engine":r["engine"],"model":r["model"],"attempted":r["attempted"],"succeeded":r["succeeded"],"failed":r["failed"],"intent_accuracy":r["intent_accuracy"],"entity_accuracy":r["entity_accuracy"],"business_action_accuracy":r["business_action_accuracy"],"critical_entity_accuracy":r["critical_entity_accuracy"],"never_guess_accuracy":r["never_guess_accuracy"],"required_action_accuracy":r["required_action_accuracy"],"missing_information_accuracy":r["missing_information_accuracy"]} for r in model_summary]
    _write_csv(output_path/"model_summary.csv",model_summary)
    _write_csv(output_path/"language_summary.csv",language_summary)
    _write_csv(output_path/"downstream_summary.csv",downstream_summary)
    return rows


def main() -> None:
    parser=argparse.ArgumentParser(description="VoiceBridge multi-ASR benchmark")
    parser.add_argument("--manifest",required=True)
    parser.add_argument("--engines",nargs="+",default=["whisper"])
    parser.add_argument("--model",default="large-v3")
    parser.add_argument("--output-dir",default="benchmark/results")
    args=parser.parse_args()
    rows=run_benchmark(args.manifest,args.engines,args.output_dir,model=args.model)
    succeeded=sum(row["status"]=="succeeded" for row in rows)
    print(f"Completed {len(rows)} runs: {succeeded} succeeded, {len(rows)-succeeded} failed.")


if __name__=="__main__":
    main()
