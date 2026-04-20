import os
import uuid
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .services import video_to_text
from utils.tools.videoTools import AsyncDouyinVideoParser
from .ai.service import optimize_text

def index(request):
    return render(request, "index.html")

@csrf_exempt
@require_http_methods(["POST"])
def api_video2text(request):
    try:
        import json
        body = json.loads(request.body) if request.body else {}
        simplified = body.get("simplified", False)

        video_file = request.FILES.get("video")
        if not video_file:
            return JsonResponse({"code": 400, "msg": "请上传视频文件"})

        temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_video")
        os.makedirs(temp_dir, exist_ok=True)
        video_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}_{video_file.name}")

        with open(video_path, "wb") as f:
            for chunk in video_file.chunks():
                f.write(chunk)

        result = video_to_text(video_path, convert_to_simplified=simplified)

        os.remove(video_path)

        return JsonResponse({
            "code": 200,
            "msg": "转写成功",
            "data": result
        })

    except Exception as e:
        return JsonResponse({"code": 500, "msg": f"失败：{str(e)}"})

@csrf_exempt
@require_http_methods(["POST"])
def api_parse_douyin(request):
    try:
        import json
        body = json.loads(request.body)
        share_url = body.get("url")
        simplified = body.get("simplified", False)

        if not share_url:
            return JsonResponse({"code": 400, "msg": "请提供抖音分享链接"})

        parser = AsyncDouyinVideoParser()
        temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_video")
        os.makedirs(temp_dir, exist_ok=True)

        result = parser.parse_and_download(share_url, temp_dir)

        video_path = result['path']
        transcription = video_to_text(video_path, convert_to_simplified=simplified)

        os.remove(video_path)

        return JsonResponse({
            "code": 200,
            "msg": "解析并转写成功",
            "data": {
                "video_url": result['url'],
                "transcription": transcription
            }
        })

    except Exception as e:
        return JsonResponse({"code": 500, "msg": f"解析失败：{str(e)}"})

@csrf_exempt
@require_http_methods(["POST"])
def api_optimize_text(request):
    try:
        import json
        body = json.loads(request.body)
        text = body.get("text", "")
        chunk_size = body.get("chunk_size", 2000)

        if not text:
            return JsonResponse({"code": 400, "msg": "没有可优化的文本"})

        result = optimize_text(text, chunk_size)

        if result.get("success"):
            return JsonResponse({
                "code": 200,
                "msg": "优化成功",
                "data": {
                    "optimized_text": result["optimized_text"],
                    "chunks": result.get("chunks", 1)
                }
            })
        else:
            return JsonResponse({
                "code": 500,
                "msg": f"优化失败：{result.get('error', '未知错误')}"
            })

    except Exception as e:
        return JsonResponse({"code": 500, "msg": f"优化失败：{str(e)}"})
