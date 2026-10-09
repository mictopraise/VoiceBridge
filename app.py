from pathlib import Path
import os
import tempfile
import wave

import av
import numpy as np

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for
from faster_whisper import WhisperModel

from action_engine import analyze_business_action
from dual_natlas import compare_transcripts
from field_testing import (
    FieldTestValidationError,
    audio_sha256,
    export_csv,
    export_json,
    find_interaction,
    load_interactions,
    load_processing_index,
    recording_manifest_csv,
    register_processed,
    safe_audio_identity,
    save_interaction,
    sanitized_summary_json,
    summarize,
)
from inference_drafts import InferenceDraftStore
from speech_engines import create_engine
from speech_engines.base import EmptyTranscriptError, ProviderUnavailableError
from speech_engines.natlas_engine import (
    NAtlasAudioTooLongError,
    NAtlasLanguageError,
)
from speech_engines.whisper_engine import WhisperEngine


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
app.config["FIELD_TEST_LOG_PATH"] = os.environ.get(
    "VOICEBRIDGE_FIELD_TEST_LOG",
    str(Path(__file__).parent / "local_data" / "field_testing" / "interactions.json"),
)
app.config["FIELD_TEST_PROCESSING_INDEX_PATH"] = os.environ.get(
    "VOICEBRIDGE_FIELD_TEST_PROCESSING_INDEX",
    str(Path(__file__).parent / "local_data" / "field_testing" / "processed.json"),
)
ALLOWED = {".opus", ".ogg", ".mp3", ".m4a", ".wav", ".webm", ".mp4"}
WHISPER_LANGUAGES = {
    "auto": (None, "Automatically detected"),
    "ha": ("ha", "Hausa"),
    "yo": ("yo", "Yoruba"),
    "ig": ("ig", "Igbo"),
    "en": ("en", "English / Nigerian Pidgin"),
}
NATLAS_LANGUAGES = {
    "yo": ("yo", "Yoruba"),
    "en-NG": ("en-NG", "Nigerian-accented English"),
}
PROVIDERS = {
    "natlas_yo": "Fast — Yoruba",
    "natlas_en": "Fast — Nigerian English",
    "dual_natlas": "Double-check — Run both N-ATLAS models",
    "whisper": "Whisper — Explicit alternative",
}
DUAL_NATLAS_LANGUAGES = {
    "dual": (None, "Yoruba-ASR + NigerianAccentedEnglish (sequential review)"),
}
NATLAS_YORUBA_LANGUAGE = {"yo": NATLAS_LANGUAGES["yo"]}
NATLAS_ENGLISH_LANGUAGE = {"en-NG": NATLAS_LANGUAGES["en-NG"]}
MODELS = {
    "small": "Small — faster",
    "medium": "Medium — more accurate",
    "large-v3": "Large v3 — best accuracy (slow on CPU)",
}
_models = {}
_provider_engines = {}
_inference_drafts = InferenceDraftStore(ttl_seconds=30 * 60)


def get_model(model_size):
    if model_size not in _models:
        _models[model_size] = WhisperModel(
            model_size, device="cpu", compute_type="int8"
        )
    return _models[model_size]


def preprocess_audio(source_path):
    """Decode locally, trim quiet edges and normalize speech to 16 kHz mono WAV."""
    container = av.open(source_path)
    stream = next((item for item in container.streams if item.type == "audio"), None)
    if stream is None:
        raise ValueError("The uploaded file does not contain an audio track.")

    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    chunks = []
    for frame in container.decode(stream):
        converted = resampler.resample(frame)
        if not isinstance(converted, list):
            converted = [converted]
        for audio_frame in converted:
            chunks.append(audio_frame.to_ndarray().reshape(-1))
    container.close()
    if not chunks:
        raise ValueError("No readable audio samples were found.")

    samples = np.concatenate(chunks).astype(np.float32)
    peak = float(np.max(np.abs(samples)))
    if peak < 1:
        raise ValueError("The recording is silent or too quiet to process.")

    threshold = max(250.0, peak * 0.025)
    active = np.flatnonzero(np.abs(samples) >= threshold)
    if active.size:
        margin = 2400
        start = max(0, int(active[0]) - margin)
        end = min(len(samples), int(active[-1]) + margin)
        samples = samples[start:end]

    samples = np.clip(samples * (28000.0 / peak), -32768, 32767).astype(np.int16)
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    handle.close()
    with wave.open(handle.name, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(samples.tobytes())
    return handle.name


def run_whisper(path, task, language=None, model_size="small"):
    result = WhisperEngine(
        model=model_size,
        model_factory=get_model,
    ).transcribe(path, task=task, language=language)
    return (
        result.transcript,
        result.detected_language,
        result.metadata["confidence"],
        result.metadata["language_probability"],
    )


def get_natlas_engine():
    if "natlas" not in _provider_engines:
        _provider_engines["natlas"] = create_engine("natlas")
    return _provider_engines["natlas"]


def run_natlas(path, language):
    """Return the normalized official N-ATLAS result without fallback."""
    return get_natlas_engine().transcribe(
        path, language=language, task="transcribe"
    )


def run_dual_natlas(path):
    """Run both official models sequentially and retain independent outcomes."""
    outputs = []
    for language, label in (("yo", "Yoruba-ASR"), ("en-NG", "NigerianAccentedEnglish")):
        model = NATLAS_LANGUAGES[language][1]
        try:
            result = run_natlas(path, language)
            outputs.append({
                "language_code": language,
                "language": model,
                "label": label,
                "model": result.model,
                "status": "completed",
                "transcript": result.transcript,
                "confidence": None,
                "error": None,
            })
        except NAtlasAudioTooLongError:
            raise
        except Exception as exc:
            outputs.append({
                "language_code": language,
                "language": model,
                "label": label,
                "model": (
                    "NCAIR1/Yoruba-ASR" if language == "yo"
                    else "NCAIR1/NigerianAccentedEnglish"
                ),
                "status": "failed",
                "transcript": "",
                "confidence": None,
                "error": f"{type(exc).__name__}: model could not process the recording",
            })
    successful = [item for item in outputs if item["status"] == "completed"]
    if not successful:
        raise ProviderUnavailableError(
            "Both N-ATLAS models failed. No fallback was performed."
        )
    if len(successful) == 2:
        comparison = compare_transcripts(
            successful[0]["transcript"], successful[1]["transcript"]
        )
    else:
        comparison = {
            "material_disagreement": True,
            "review_required": True,
            "categories": {"technical_model_failure": {
                "failed_models": [item["model"] for item in outputs if item["status"] == "failed"]
            }},
            "token_similarity_for_routing_only": None,
            "confidence": None,
            "correct_model": None,
            "notice": "One N-ATLAS model failed — human review required.",
        }
    return outputs, comparison


def confidence_message(confidence, language_probability, forced_language):
    if confidence < 45:
        return "Low confidence: please listen and correct the transcript before using it."
    if not forced_language and language_probability < 65:
        return "Language detection is uncertain. Select the spoken language and process again."
    if confidence < 70:
        return "Fair confidence: review names, prices and product details carefully."
    return "Good confidence, but always verify important business details before replying."


def suggest_reply(english):
    english = (english or "").strip()
    text = english.lower()
    if any(word in text for word in ("price", "cost", "how much", "charge")):
        return ("Thank you for your interest. Our introductory package is ₦5,000 for one "
                "8–10 second promotional product video, including music, text, your logo, "
                "one revision and delivery within 48 hours. Please send your business name "
                "and clear product photos so I can review them.")
    if any(word in text for word in ("sample", "example", "portfolio", "previous work")):
        return ("Thank you for your interest. I’ll be happy to share samples of our product "
                "animation work. Please also send your business name and the product you want "
                "to promote so I can recommend the right video style.")
    if any(word in text for word in ("location", "where are you", "based", "address")):
        return ("Thank you for reaching out. We are based in Ibadan and work with businesses "
                "across Nigeria because the service is delivered online. Please send clear "
                "product photos and your business name to get started.")
    if any(word in text for word in ("delivery", "how long", "when", "ready")):
        return ("Thank you for your interest. Standard delivery is within 48 hours after we "
                "receive your product photos, details and deposit. Please send your business "
                "name and clear product photos to begin.")
    return ("Thank you for contacting Laundrypal Creative Studio. We create short promotional "
            "product videos for WhatsApp, Instagram and Facebook. Please send your business "
            "name and clear product photos so I can recommend the best concept for you.")


@app.post("/suggest-reply")
def suggest_reply_api():
    payload = request.get_json(silent=True) or {}
    english = str(payload.get("english", "")).strip()
    if not english:
        return jsonify({"error": "Enter or correct the English meaning first."}), 400
    return jsonify({"reply": suggest_reply(english)})


@app.post("/analyze-action")
def analyze_action_api():
    payload = request.get_json(silent=True) or {}
    transcript = str(payload.get("transcript", "")).strip()
    english = str(payload.get("english", "")).strip()
    if not transcript and not english:
        return jsonify({"error": "Enter a transcript or English meaning first."}), 400
    action = analyze_business_action(
        transcript=transcript,
        english=english,
        asr_language=payload.get("language"),
        asr_confidence=payload.get("confidence"),
    )
    raw_transcript = str(payload.get("raw_transcript", transcript)).strip()
    raw_english = str(payload.get("raw_english", english)).strip()
    return jsonify({
        "action": action,
        "correction_provenance": {
            "raw_provider_transcript_preserved": raw_transcript,
            "transcript_user_corrected": transcript != raw_transcript,
            "english_user_corrected": english != raw_english,
        },
    })


def _field_test_records():
    return load_interactions(app.config["FIELD_TEST_LOG_PATH"])


def _processed_records():
    return load_processing_index(app.config["FIELD_TEST_PROCESSING_INDEX_PATH"])


@app.post("/field-testing/draft")
def create_field_test_draft():
    payload = request.get_json(silent=True) or {}
    seed_token = str(payload.get("seed_token", ""))
    seed = _inference_drafts.consume(seed_token)
    if seed is None:
        return jsonify({
            "error": "This inference result is missing or expired. Process the audio again."
        }), 410
    working = str(payload.get("working_transcript", "")).strip()
    english = str(payload.get("english_meaning", "")).strip()
    starting_model = str(payload.get("starting_model", "")).strip()
    model_outputs = seed.get("model_outputs") or []
    if seed.get("processing_mode") == "dual_natlas_review":
        selected = next(
            (item for item in model_outputs
             if item.get("model") == starting_model and item.get("status") == "completed"),
            None,
        )
        if selected is None:
            return jsonify({
                "error": "Choose one successful model output as the working-transcript starting point."
            }), 400
        raw = str(selected.get("transcript", "")).strip()
        seed["starting_model"] = selected["model"]
        seed["starting_language"] = selected["language"]
    else:
        raw = str(seed.get("raw_provider_transcript", "")).strip()
    if not raw:
        return jsonify({"error": "The immutable provider transcript is missing."}), 400
    action = analyze_business_action(
        transcript=working or raw,
        english=english,
        asr_language=seed.get("language_code"),
        asr_confidence=seed.get("confidence"),
    )
    draft = {
        **seed,
        "processing_status": "completed",
        "raw_provider_transcript": raw[:5000],
        "working_transcript": (working or raw)[:5000],
        "english_meaning": english[:5000],
        "action": action,
    }
    token = _inference_drafts.create(draft)
    return jsonify({"review_url": url_for("field_testing", draft=token)})


@app.route("/field-testing", methods=["GET", "POST"])
def field_testing():
    error = None
    saved = request.args.get("saved")
    updated = request.args.get("updated")
    draft_token = request.args.get("draft") or request.form.get("draft_token")
    draft = _inference_drafts.get(draft_token)
    if draft_token and draft is None:
        error = "This inference draft is missing or expired. Process the audio again."
    if request.method == "POST":
        try:
            payload = request.form.to_dict()
            if draft:
                payload.update({
                    key: draft[key] for key in (
                        "audio_filename", "audio_code", "recording_key", "provider",
                        "model", "selected_language", "selected_language_source",
                        "processing_status", "raw_provider_transcript",
                        "working_transcript", "english_meaning",
                        "processing_mode", "material_disagreement",
                        "disagreement_categories", "model_outputs", "starting_model",
                    )
                    if key in draft
                })
                if draft["action"].get("needs_confirmation"):
                    payload["never_guess_triggered"] = "true"
            outcome = save_interaction(app.config["FIELD_TEST_LOG_PATH"], payload)
            if draft_token:
                _inference_drafts.consume(draft_token)
            parameter = "saved" if outcome["created"] else "updated"
            return redirect(url_for(
                "field_testing", **{parameter: outcome["record"]["interaction_id"]}
            ))
        except FieldTestValidationError as exc:
            error = str(exc)
    try:
        records = _field_test_records()
    except FieldTestValidationError as exc:
        records = []
        error = str(exc)
    duplicate = find_interaction(records, draft.get("recording_key")) if draft else None
    return render_template(
        "field_testing.html",
        error=error,
        saved=saved,
        updated=updated,
        draft=draft,
        draft_token=draft_token if draft else "",
        duplicate=duplicate,
        summary=summarize(records, _processed_records()),
        recent=list(reversed(records[-10:])),
    )


@app.get("/field-testing/export.csv")
def field_testing_csv():
    return Response(
        export_csv(_field_test_records()),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=voicebridge-field-tests.csv"},
    )


@app.get("/field-testing/export.json")
def field_testing_json():
    return Response(
        export_json(_field_test_records()),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=voicebridge-field-tests.json"},
    )


@app.get("/field-testing/sanitized-summary.json")
def field_testing_sanitized_summary():
    return Response(
        sanitized_summary_json(_field_test_records(), _processed_records()),
        mimetype="application/json",
        headers={
            "Content-Disposition":
                "attachment; filename=voicebridge-field-test-summary-sanitized.json"
        },
    )


@app.get("/field-testing/recording-manifest.csv")
def field_testing_recording_manifest():
    return Response(
        recording_manifest_csv(_processed_records(), _field_test_records()),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=voicebridge-recording-manifest.csv"
        },
    )


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    natlas_failed = False
    submitted_provider = request.form.get("provider", "dual_natlas")
    unsupported_provider = submitted_provider not in {*PROVIDERS, "natlas"}
    provider_choice = submitted_provider
    if unsupported_provider:
        provider_choice = "dual_natlas"
    language_catalog = (
        DUAL_NATLAS_LANGUAGES if provider_choice == "dual_natlas"
        else NATLAS_YORUBA_LANGUAGE if provider_choice == "natlas_yo"
        else NATLAS_ENGLISH_LANGUAGE if provider_choice == "natlas_en"
        else NATLAS_LANGUAGES if provider_choice == "natlas"
        else WHISPER_LANGUAGES
    )
    default_language = (
        "dual" if provider_choice == "dual_natlas"
        else "yo" if provider_choice in {"natlas", "natlas_yo"}
        else "en-NG" if provider_choice == "natlas_en" else "auto"
    )
    submitted_language = request.form.get("language", default_language)
    unsupported_language = submitted_language not in language_catalog
    language_choice = submitted_language
    if unsupported_language:
        language_choice = default_language
    if request.method == "POST":
        forced_language, selected_label = language_catalog[language_choice]
        model_size = request.form.get("model_size", "small")
        if model_size not in MODELS:
            model_size = "small"
        upload = request.files.get("audio")
        if unsupported_provider:
            error = (
                "That speech provider is not supported. No provider was selected or run "
                "automatically."
            )
        elif unsupported_language:
            natlas_failed = provider_choice in {"natlas", "natlas_yo", "natlas_en", "dual_natlas"}
            error = (
                "That language is not supported by the selected provider. "
                "N-ATLAS currently exposes Yoruba and Nigerian-accented English only."
            )
        elif not upload or not upload.filename:
            error = "Please choose a WhatsApp voice note or audio file."
        else:
            suffix = Path(upload.filename).suffix.lower()
            if suffix not in ALLOWED:
                error = "Unsupported file. Use OPUS, OGG, MP3, M4A, WAV, WEBM or MP4."
            else:
                temp_path = None
                processed_path = None
                identity = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        upload.save(tmp)
                        temp_path = tmp.name
                    identity = safe_audio_identity(
                        upload.filename, audio_sha256(temp_path)
                    )
                    processed_path = preprocess_audio(temp_path)
                    if provider_choice == "dual_natlas":
                        model_outputs, comparison = run_dual_natlas(processed_path)
                        result = {
                            "provider": "dual_natlas",
                            "processing_mode": "dual_natlas_review",
                            "speech_provider": "NCAIR N-ATLAS",
                            "model": "NCAIR1/Yoruba-ASR + NCAIR1/NigerianAccentedEnglish",
                            "language": "Two explicit model evaluations",
                            "language_code": "dual",
                            "language_source": "Fixed by Dual N-ATLAS Review mode; not auto-detected",
                            "model_outputs": model_outputs,
                            "comparison": comparison,
                            "raw_transcript": "",
                            "transcript": "",
                            "raw_english": "",
                            "english": "",
                            "translation_provider": "Not generated",
                            "transcript_user_corrected": False,
                            "confidence": None,
                            "confidence_message": (
                                "Neither N-ATLAS model supplies calibrated confidence. "
                                "Review both immutable outputs and choose a starting transcript."
                            ),
                            "fallback_status": "None",
                            "translation_by_natlas": False,
                        }
                    elif provider_choice in {"natlas", "natlas_yo", "natlas_en"}:
                        asr = run_natlas(processed_path, forced_language)
                        raw_transcript = asr.transcript
                        english = ""
                        translation_provider = "Not generated"
                        if forced_language == "yo":
                            try:
                                english, _, _, _ = run_whisper(
                                    processed_path, "translate", "yo", model_size
                                )
                                translation_provider = "Local Whisper translation"
                            except Exception:
                                english = ""
                        elif forced_language == "en-NG":
                            english = raw_transcript
                            translation_provider = "Not generated — source is English"
                        result = {
                            "provider": "natlas",
                            "speech_provider": "NCAIR N-ATLAS",
                            "model": asr.model,
                            "language": selected_label,
                            "language_code": forced_language,
                            "language_source": "Explicit user selection",
                            "raw_transcript": raw_transcript,
                            "transcript": raw_transcript,
                            "raw_english": english,
                            "english": english,
                            "translation_provider": translation_provider,
                            "transcript_user_corrected": False,
                            "confidence": None,
                            "confidence_message": (
                                "Provider confidence is not supplied. VoiceBridge will require "
                                "confirmation for critical business fields."
                            ),
                            "fallback_status": "None",
                            "translation_by_natlas": False,
                        }
                    else:
                        transcript, detected, confidence, language_probability = run_whisper(
                            processed_path, "transcribe", forced_language, model_size
                        )
                        english, _, translation_confidence, _ = run_whisper(
                            processed_path, "translate", forced_language or detected, model_size
                        )
                        if not transcript:
                            raise ValueError("No clear speech was detected.")
                        combined_confidence = min(confidence, translation_confidence)
                        result = {
                            "provider": "whisper",
                            "speech_provider": "Local Whisper",
                            "model": model_size,
                            "language": selected_label if forced_language else detected.upper(),
                            "language_code": forced_language or detected,
                            "language_source": (
                                "Explicit user selection" if forced_language else "Automatic detection"
                            ),
                            "raw_transcript": transcript,
                            "transcript": transcript,
                            "raw_english": english,
                            "english": english,
                            "translation_provider": "Local Whisper translation",
                            "transcript_user_corrected": False,
                            "confidence": combined_confidence,
                            "confidence_message": confidence_message(
                                combined_confidence, language_probability, forced_language
                            ),
                            "fallback_status": "None — explicitly selected provider",
                            "translation_by_natlas": False,
                        }
                    result["action"] = analyze_business_action(
                        transcript=result["raw_transcript"],
                        english=result["english"],
                        asr_language=result["language_code"],
                        asr_confidence=result["confidence"],
                    )
                    result["reply"] = (
                        result["action"]["suggested_reply"]
                        if result["confidence"] is None or result["confidence"] >= 45
                        else None
                    )
                    result.update(identity)
                    result["processing_status"] = "completed"
                    register_processed(
                        app.config["FIELD_TEST_PROCESSING_INDEX_PATH"],
                        identity,
                        result["speech_provider"],
                        result["model"],
                    )
                    result["field_test_seed"] = _inference_drafts.create({
                        "audio_filename": result["audio_filename"],
                        "audio_code": result["audio_code"],
                        "recording_key": result["recording_key"],
                        "provider": result["speech_provider"],
                        "model": result["model"],
                        "selected_language": result["language"],
                        "selected_language_source": result["language_source"],
                        "language_code": result["language_code"],
                        "confidence": result["confidence"],
                        "raw_provider_transcript": result["raw_transcript"],
                        "processing_mode": result.get("processing_mode", "single_model"),
                        "material_disagreement": result.get("comparison", {}).get(
                            "material_disagreement", False
                        ),
                        "disagreement_categories": result.get("comparison", {}).get(
                            "categories", {}
                        ),
                        "model_outputs": result.get("model_outputs", []),
                    })
                except NAtlasAudioTooLongError:
                    natlas_failed = True
                    error = (
                        "N-ATLAS currently supports recordings up to 30 seconds in this build. "
                        "Please upload a shorter clip or explicitly choose local Whisper."
                    )
                except (NAtlasLanguageError, ProviderUnavailableError, EmptyTranscriptError):
                    natlas_failed = provider_choice in {"natlas", "natlas_yo", "natlas_en", "dual_natlas"}
                    error = (
                        "N-ATLAS could not process this recording. No fallback was performed."
                        if natlas_failed else
                        "The selected speech provider could not process this recording."
                    )
                except Exception as exc:
                    natlas_failed = provider_choice in {"natlas", "natlas_yo", "natlas_en", "dual_natlas"}
                    error = (
                        "N-ATLAS could not process this recording. No fallback was performed."
                        if natlas_failed else
                        f"The voice note could not be processed: {exc}"
                    )
                finally:
                    if temp_path and os.path.exists(temp_path):
                        os.unlink(temp_path)
                    if processed_path and os.path.exists(processed_path):
                        os.unlink(processed_path)
    return render_template(
        "index.html", result=result, error=error,
        providers=PROVIDERS, selected_provider=provider_choice,
        languages=language_catalog, selected=language_choice,
        whisper_languages=WHISPER_LANGUAGES, natlas_languages=NATLAS_LANGUAGES,
        dual_natlas_languages=DUAL_NATLAS_LANGUAGES,
        natlas_yoruba_language=NATLAS_YORUBA_LANGUAGE,
        natlas_english_language=NATLAS_ENGLISH_LANGUAGE,
        models=MODELS, selected_model=request.form.get("model_size", "small"),
        natlas_failed=natlas_failed,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
