# -*- coding: utf-8 -*-
import sys
import io
import shutil
import os
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from gradio_client import Client, handle_file

API_URL = "http://localhost:9872/"
OUTPUT_DIR = "tests/output"

def test_tts():
    print("[TEST] Starting GPT-SoVITS API Test...")
    print(f"[TEST] API URL: {API_URL}")

    client = Client(API_URL)

    ref_audio_dir = "temp/ref_audio"
    ref_audio_files = [f for f in os.listdir(ref_audio_dir) if f.endswith('.wav')]
    ref_audio = os.path.join(ref_audio_dir, ref_audio_files[0]) if ref_audio_files else None
    if not ref_audio:
        raise Exception(f"No reference audio found in {ref_audio_dir}")
    prompt_text = "圈里或者任何地方去找五样东西，去看看五样东西，然后去听四种声音。"

    aux_audio_dir = "temp/aux_audio"
    aux_ref_audio_paths = []
    if os.path.exists(aux_audio_dir):
        for f in sorted(os.listdir(aux_audio_dir)):
            if f.endswith('.wav'):
                aux_ref_audio_paths.append(handle_file(os.path.join(aux_audio_dir, f)))

    print(f"[TEST] Reference Audio: {ref_audio}")
    print(f"[TEST] Prompt Text: {prompt_text}")
    print(f"[TEST] Aux Reference Audios: {len(aux_ref_audio_paths)} files")
    print("[TEST] Calling /inference API...")

    result = client.predict(
        text="你好，这是GPT-SoVITS语音合成测试。",
        text_lang="中文",
        ref_audio_path=handle_file(ref_audio),
        aux_ref_audio_paths=aux_ref_audio_paths,
        prompt_text=prompt_text,
        prompt_lang="中文",
        ref_text_free=False,
        batch_size=20,
        fragment_interval=0.3,
        speed_factor=1,
        top_k=5,
        top_p=1.0,
        temperature=1.0,
        repetition_penalty=1.35,
        text_split_method="不切",
        split_bucket=True,
        parallel_infer=True,
        keep_random=True,
        seed=-1,
        sample_steps=32,
        super_sampling=False,
        api_name="/inference"
    )

    temp_audio_path = result[0]
    output_filename = f"tts_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    output_path = f"{OUTPUT_DIR}/{output_filename}"

    shutil.copy(temp_audio_path, output_path)
    print(f"[SUCCESS] Output Audio saved: {output_path}")
    print(f"[SUCCESS] Random Seed: {result[1]}")
    return result


if __name__ == "__main__":
    try:
        test_tts()
        print("[OK] Test completed successfully!")
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
