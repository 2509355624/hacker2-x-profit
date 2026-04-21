import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import whisper
import srt
import zhconv
from datetime import timedelta

ffmpeg_path = os.getenv("FFMPEG_PATH")
if ffmpeg_path:
    os.environ["PATH"] = ffmpeg_path + ";" + os.environ.get("PATH", "")

MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
LANGUAGE = os.getenv("WHISPER_LANGUAGE", "zh")

MODEL = None

def load_whisper_model():
    global MODEL
    if MODEL is None:
        MODEL = whisper.load_model(MODEL_SIZE)
    return MODEL

def to_simplified(text):
    return zhconv.convert(text, 'zh-hans')

def transcribe(audio_path, convert_to_simplified=False):
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

    return {
        "full_text": full_text,
        "srt_content": srt_content,
        "segments": result["segments"]
    }

if __name__ == "__main__":
    audio_path = sys.argv[1]
    convert_to_simplified = sys.argv[2].lower() == 'true' if len(sys.argv) > 2 else False

    import json
    result = transcribe(audio_path, convert_to_simplified)
    print(json.dumps(result, ensure_ascii=False))