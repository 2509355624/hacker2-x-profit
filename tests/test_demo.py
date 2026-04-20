import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["PATH"] = r"D:\ffmpeg\ffmpeg\ffmpeg\bin;" + os.environ.get("PATH", "")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "video2text.settings")

import django
django.setup()

from utils.tools.videoTools import AsyncDouyinVideoParser

DOUYIN_URL = "https://v.douyin.com/R4mjTCcGW3g/"

def test_parse_only():
    print("=" * 50)
    print("测试1: 仅解析抖音链接")
    print("=" * 50)
    parser = AsyncDouyinVideoParser()
    try:
        result = parser.parse_video_url(DOUYIN_URL)
        print(f"解析成功: {result}")
        return result
    except Exception as e:
        print(f"解析失败: {e}")
        return None

def test_parse_and_download():
    print("\n" + "=" * 50)
    print("测试2: 解析并下载视频")
    print("=" * 50)
    parser = AsyncDouyinVideoParser()
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media", "temp_video")

    try:
        result = parser.parse_and_download(DOUYIN_URL, output_dir)
        print(f"下载成功: {result}")
        return result
    except Exception as e:
        print(f"下载失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_transcribe(video_path):
    print("\n" + "=" * 50)
    print("测试3: 转写视频")
    print("=" * 50)
    if not video_path or not os.path.exists(video_path):
        print(f"视频文件不存在: {video_path}")
        return None

    try:
        from app.services import video_to_text
        result = video_to_text(video_path)
        print(f"转写成功!")
        print(f"文本长度: {len(result['full_text'])} 字符")
        print(f"字幕片段数: {len(result['segments'])}")
        return result
    except Exception as e:
        print(f"转写失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print(f"测试链接: {DOUYIN_URL}\n")
    print(f"FFmpeg 路径: D:\\ffmpeg\\ffmpeg\\ffmpeg\\bin\n")

    result = test_parse_only()
    if result:
        download_result = test_parse_and_download()
        if download_result and download_result.get('path'):
            transcribe_result = test_transcribe(download_result['path'])
            if transcribe_result:
                print("\n" + "=" * 50)
                print("全部测试通过!")
                print("=" * 50)
                print(f"\n转写文本预览:\n{transcribe_result['full_text'][:500]}...")

if __name__ == "__main__":
    main()
