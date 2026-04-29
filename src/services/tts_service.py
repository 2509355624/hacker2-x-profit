# -*- coding: utf-8 -*-
import sys
import io
import os
import json
import shutil
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import warnings
warnings.filterwarnings('ignore')

os.environ['GRADIO_CLIENT_LOG'] = '0'
os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'

from gradio_client import Client, handle_file

API_URL = "http://localhost:9872/"
OUTPUT_DIR = "d:/gitlab/hacker2-x-profit/output_audio"

def get_default_params():
    return {
        'text_lang': '中文',
        'aux_ref_audio_paths': [],
        'prompt_lang': '中文',
        'top_k': 5,
        'top_p': 1.0,
        'temperature': 1.0,
        'text_split_method': '不切',
        'batch_size': 20,
        'speed_factor': 1,
        'ref_text_free': True,
        'split_bucket': True,
        'fragment_interval': 0.3,
        'seed': -1,
        'keep_random': True,
        'parallel_infer': True,
        'repetition_penalty': 1.35,
        'sample_steps': 32,
        'super_sampling': False,
    }

def tts_inference(text, ref_audio_path, prompt_text, params=None):
    if params is None:
        params = {}

    default_params = get_default_params()
    default_params.update(params)

    client = Client(API_URL, verbose=False)

    aux_ref_audio_paths_list = []
    for aux_path in sorted(default_params.get('aux_ref_audio_paths', [])):
        aux_ref_audio_paths_list.append(handle_file(aux_path))

    result = client.predict(
        text=text,
        text_lang=default_params['text_lang'],
        ref_audio_path=handle_file(ref_audio_path),
        aux_ref_audio_paths=aux_ref_audio_paths_list,
        prompt_text=prompt_text,
        prompt_lang=default_params['prompt_lang'],
        top_k=default_params['top_k'],
        top_p=default_params['top_p'],
        temperature=default_params['temperature'],
        text_split_method=default_params['text_split_method'],
        batch_size=default_params['batch_size'],
        speed_factor=default_params['speed_factor'],
        ref_text_free=default_params['ref_text_free'],
        split_bucket=default_params['split_bucket'],
        fragment_interval=default_params['fragment_interval'],
        seed=default_params['seed'],
        keep_random=default_params['keep_random'],
        parallel_infer=default_params['parallel_infer'],
        repetition_penalty=default_params['repetition_penalty'],
        sample_steps=default_params['sample_steps'],
        super_sampling=default_params['super_sampling'],
        api_name="/inference"
    )

    return result

def tts_inference_with_save(text, ref_audio_path, prompt_text, params=None):
    result = tts_inference(text, ref_audio_path, prompt_text, params)
    audio_path = result[0]
    seed = result[1]

    if not audio_path:
        raise Exception("API返回的音频路径为空")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_filename = f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    shutil.copy(audio_path, output_path)

    try:
        os.remove(audio_path)
    except:
        pass

    return {
        "success": True,
        "audio_path": f"/output_audio/{output_filename}",
        "temp_audio_path": audio_path,
        "seed": seed
    }

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(json.dumps({"error": "Usage: python tts_service.py <text> <ref_audio_path> <prompt_text> [params_json]"}))
        sys.exit(1)

    text = sys.argv[1]
    ref_audio_path = sys.argv[2]
    prompt_text = sys.argv[3]
    params = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}

    try:
        result = tts_inference_with_save(text, ref_audio_path, prompt_text, params)
        print(json.dumps(result), flush=True)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(json.dumps({"error": str(e)}), flush=True)
        sys.exit(1)
