from pathlib import Path
import os
import tempfile
import wave

import av
import numpy as np

from flask import Flask, jsonify, render_template, request
from faster_whisper import WhisperModel

from action_engine import analyze_business_action
from speech_engines.whisper_engine import WhisperEngine


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
ALLOWED = {".opus", ".ogg", ".mp3", ".m4a", ".wav", ".webm", ".mp4"}
LANGUAGES = {
    "auto": (None, "Automatically detected"),
    "ha": ("ha", "Hausa"),
    "yo": ("yo", "Yoruba"),
    "ig": ("ig", "Igbo"),
    "en": ("en", "English / Nigerian Pidgin"),
}
MODELS = {
    "small": "Small — faster",
    "medium": "Medium — more accurate",
    "large-v3": "Large v3 — best accuracy (slow on CPU)",
}
_models = {}


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
    return jsonify({"action": action})


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    if request.method == "POST":
        language_choice = request.form.get("language", "auto")
        if language_choice not in LANGUAGES:
            language_choice = "auto"
        forced_language, selected_label = LANGUAGES[language_choice]
        model_size = request.form.get("model_size", "small")
        if model_size not in MODELS:
            model_size = "small"
        upload = request.files.get("audio")
        if not upload or not upload.filename:
            error = "Please choose a WhatsApp voice note or audio file."
        else:
            suffix = Path(upload.filename).suffix.lower()
            if suffix not in ALLOWED:
                error = "Unsupported file. Use OPUS, OGG, MP3, M4A, WAV, WEBM or MP4."
            else:
                temp_path = None
                processed_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        upload.save(tmp)
                        temp_path = tmp.name
                    processed_path = preprocess_audio(temp_path)
                    transcript, detected, confidence, language_probability = run_whisper(
                        processed_path, "transcribe", forced_language, model_size
                    )
                    english, _, translation_confidence, _ = run_whisper(
                        processed_path, "translate", forced_language or detected, model_size
                    )
                    if not transcript:
                        raise ValueError("No clear speech was detected.")
                    result = {
                        "language": selected_label if forced_language else detected.upper(),
                        "language_code": forced_language or detected,
                        "transcript": transcript,
                        "english": english,
                        "confidence": min(confidence, translation_confidence),
                        "confidence_message": confidence_message(
                            min(confidence, translation_confidence),
                            language_probability,
                            forced_language,
                        ),
                    }
                    result["action"] = analyze_business_action(
                        transcript=transcript,
                        english=english,
                        asr_language=forced_language or detected,
                        asr_confidence=result["confidence"],
                    )
                    result["reply"] = (
                        result["action"]["suggested_reply"]
                        if result["confidence"] >= 45
                        else None
                    )
                except Exception as exc:
                    error = f"The voice note could not be processed: {exc}"
                finally:
                    if temp_path and os.path.exists(temp_path):
                        os.unlink(temp_path)
                    if processed_path and os.path.exists(processed_path):
                        os.unlink(processed_path)
    return render_template(
        "index.html", result=result, error=error,
        languages=LANGUAGES, selected=request.form.get("language", "auto"),
        models=MODELS, selected_model=request.form.get("model_size", "small")
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
