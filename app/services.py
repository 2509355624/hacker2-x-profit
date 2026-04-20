import os
import uuid
import whisper
import srt
import ffmpeg
import zhconv
from datetime import timedelta
from django.conf import settings

ffmpeg_path = os.getenv("FFMPEG_PATH")
if ffmpeg_path:
    os.environ["PATH"] = ffmpeg_path + ";" + os.environ.get("PATH", "")

MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
MODEL_PATH = os.getenv("WHISPER_MODEL_PATH")
LANGUAGE = os.getenv("WHISPER_LANGUAGE", "zh")

MODEL = None

def load_whisper_model():
    global MODEL
    if MODEL is None:
        if MODEL_PATH and os.path.exists(MODEL_PATH):
            MODEL = whisper.load_model(MODEL_PATH)
        else:
            MODEL = whisper.load_model(MODEL_SIZE)
    return MODEL

def extract_audio(video_path: str, output_dir: str) -> str:
    audio_name = f"{uuid.uuid4().hex}.wav"
    audio_path = os.path.join(output_dir, audio_name)

    ffmpeg.input(video_path).output(
        audio_path, ac=1, ar=16000, format="wav", loglevel="error"
    ).run(overwrite_output=True)
    return audio_path

def to_simplified(text: str) -> str:
    return zhconv.convert(text, 'zh-hans')

def video_to_text(video_path: str, convert_to_simplified: bool = False):
    temp_audio_dir = os.path.join(settings.MEDIA_ROOT, "temp_audio")
    os.makedirs(temp_audio_dir, exist_ok=True)

    audio_path = extract_audio(video_path, temp_audio_dir)

    model = load_whisper_model()
    result = model.transcribe(audio_path, language=LANGUAGE, verbose=False)

    full_text = "\n".join([seg["text"].strip() for seg in result["segments"]])

    if convert_to_simplified:
        full_text = to_simplified(full_text)

    subtitles = []
    for i, seg in enumerate(result["segments"], 1):
        content = seg["text"].strip()
        if convert_to_simplified:
            content = to_simplified(content)
        subtitles.append(srt.Subtitle(
            index=i,
            start=timedelta(seconds=seg["start"]),
            end=timedelta(seconds=seg["end"]),
            content=content
        ))
    srt_content = srt.compose(subtitles)

    os.remove(audio_path)

    return {
        "full_text": full_text,
        "srt_content": srt_content,
        "segments": result["segments"]
    }
