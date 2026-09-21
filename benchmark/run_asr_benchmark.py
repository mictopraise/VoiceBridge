"""Run a frozen speech-only benchmark without invoking VoiceBridge business logic."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Callable

from speech_engines import create_engine
from speech_engines.provider_cache import sha256_file

from .manifest import load_manifest
from .metrics import speech_metrics


def resolve_audio(manifest_path: Path, sample: dict) -> Path:
    direct=manifest_path.parent/sample["audio_path"]
    if direct.is_file(): return direct.resolve()
    config=sample.get("dataset_config") or sample.get("language")
    return (manifest_path.parent/"audio"/str(config)/sample["audio_path"]).resolve()


def summarize(rows:list[dict],group_fields:tuple[str,...])->list[dict]:
    groups={}
    for row in rows: groups.setdefault(tuple(row.get(f,"") for f in group_fields),[]).append(row)
    output=[]
    for group,items in sorted(groups.items()):
        successful=[r for r in items if r["status"]=="succeeded"]
        result=dict(zip(group_fields,group))
        result.update(attempted=len(items),succeeded=len(successful),failed=len(items)-len(successful),audio_seconds=sum(float(r.get("audio_seconds") or 0) for r in successful),total_processing_seconds=sum(float(r.get("asr_processing_seconds") or 0) for r in successful))
        for metric,errors,denominator in (("wer","word_errors","reference_words"),("cer","character_errors","reference_characters"),("strict_wer","strict_word_errors","strict_reference_words"),("strict_cer","strict_character_errors","strict_reference_characters")):
            total=sum(r.get(errors,0) for r in successful); count=sum(r.get(denominator,0) for r in successful); result[metric]=total/count if count else None
        duration=result["audio_seconds"]; result["real_time_factor"]=result["total_processing_seconds"]/duration if duration else None
        output.append(result)
    return output


def _write_csv(path:Path,rows:list[dict])->None:
    if not rows:return
    with path.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator="\n"); writer.writeheader(); writer.writerows(rows)


def run_asr_benchmark(manifest_path:str|Path,output_dir:str|Path,*,model:str,engine_name:str="whisper",engine_factory:Callable[...,object]=create_engine)->list[dict]:
    manifest_path=Path(manifest_path); samples=load_manifest(manifest_path); destination=Path(output_dir); destination.mkdir(parents=True,exist_ok=True); engine=engine_factory(engine_name,model=model); rows=[]
    for sample in samples:
        audio_path=resolve_audio(manifest_path,sample)
        base={"sample_id":sample["sample_id"],"dataset":sample.get("dataset",""),"dataset_config":sample.get("dataset_config",""),"language_pair":sample.get("language_pair",""),"engine":engine_name,"model":getattr(engine,"model",model),"reference_transcript":sample["reference_transcript"]}
        try:
            if not audio_path.is_file(): raise FileNotFoundError(f"Audio file not found: {sample['audio_path']}")
            result=engine.transcribe(str(audio_path),language=sample.get("forced_language"))
            metrics=speech_metrics(sample["reference_transcript"],result.transcript)
            rows.append({**base,"status":"succeeded","audio_sha256":sha256_file(audio_path),"raw_transcript":result.transcript,"normalized_asr":result.to_dict(),"detected_language":result.detected_language,**metrics,"audio_seconds":result.audio_seconds,"asr_processing_seconds":result.processing_seconds,"real_time_factor":result.processing_seconds/result.audio_seconds if result.audio_seconds else None,"error_type":None,"error":None})
        except Exception as exc:
            rows.append({**base,"status":"failed","audio_sha256":sha256_file(audio_path) if audio_path.is_file() else None,"error_type":type(exc).__name__,"error":str(exc)})
    with (destination/"raw_results.jsonl").open("w",encoding="utf-8") as handle:
        for row in rows: handle.write(json.dumps(row,ensure_ascii=False)+"\n")
    _write_csv(destination/"model_summary.csv",summarize(rows,("engine","model")))
    _write_csv(destination/"language_summary.csv",summarize(rows,("engine","model","dataset_config","language_pair")))
    return rows


def main()->None:
    parser=argparse.ArgumentParser(description="VoiceBridge ASR-only benchmark")
    parser.add_argument("--manifest",required=True);parser.add_argument("--output-dir",required=True);parser.add_argument("--engine",default="whisper");parser.add_argument("--model",required=True)
    args=parser.parse_args();rows=run_asr_benchmark(args.manifest,args.output_dir,engine_name=args.engine,model=args.model);succeeded=sum(row["status"]=="succeeded" for row in rows);print(f"Completed {len(rows)} runs: {succeeded} succeeded, {len(rows)-succeeded} failed.")


if __name__=="__main__":
    main()
