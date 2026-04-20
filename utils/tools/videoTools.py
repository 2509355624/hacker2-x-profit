import json
import os
import uuid

import requests
import re
from urllib.parse import urlparse, parse_qs, unquote
from lxml import html
from utils.tools.exceptionTools import CustomException, CustomErrors
from utils.cacheTools.redisTools import RedisQueue
from datetime import datetime


def _extract_domain(url):
    if not url or len(url) < 4:
        return None

    if 'http://' in url:
        cleaned_url = 'http://' + url.split('http://', 1)[1]
    elif 'https://' in url:
        cleaned_url = 'https://' + url.split('https://', 1)[1]
    else:
        return None

    parsed = urlparse(cleaned_url)
    domain = parsed.netloc or parsed.path.split('/')[0]

    if domain:
        if domain.startswith('www.'):
            domain = domain[4:]
        if '.' in domain:
            return domain
    return None

def get_redis_video_error_list():
    redis_video_error = RedisQueue('video_error_msg')
    all_keys = redis_video_error.getKeys('video_error_msg:*')
    data_list = redis_video_error.batchGetStr(all_keys)

    error_list = []

    for key, value in zip(all_keys, data_list):
        domain = _extract_domain(key) or 'unknown'
        value = json.loads(value)

        error_list.append({
            'domain': domain,
            'share_url': key,
            'error_msg': value['error_msg'],
            'time': value['time']
        })

    error_list.sort(
        key=lambda x: datetime.strptime(x["time"], "%Y-%m-%d %H:%M:%S"),
        reverse=True
    )

    return error_list

class AsyncDouyinVideoParser:
    DOUYIN_DOMAIN = 'douyin.com'
    DOUYIN_BASE_URL = 'https://www.douyin.com'
    PLAY_API_BASE_URL = 'https://www.iesdouyin.com/aweme/v1/play/'
    VIDEO_PLAYER_ID = 'video-player'
    VIDEO_ID_PARAM = 'video_id'

    REDIRECT_STATUS_CODES = (301, 302, 303, 307, 308)
    SUCCESS_STATUS_CODE = 200

    HEAD_REQUEST_TIMEOUT = 5
    GET_REQUEST_TIMEOUT = 8
    DOWNLOAD_TIMEOUT = 60

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            'Referer': self.DOUYIN_BASE_URL + '/'
        }
        self.redis_video_error = None
        self.err_msg = ""

    def post_video_error_msg(self, error_msg):
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = json.dumps({'error_msg': error_msg, 'time': time})
        self.redis_video_error.addStrEX(60*60*24*30, data)

    def parse_video_url(self, share_url):
        self.redis_video_error = RedisQueue('video_error_msg:' + share_url)
        cleaned_url = self._clean_and_validate_url(share_url)
        detail_url = self.get_douyin_detail_url(cleaned_url)
        html_content = self.get_douyin_html(detail_url)
        video_id = self.extract_video_id_from_html(html_content)
        url = f"{self.PLAY_API_BASE_URL}?{video_id}"
        return {'url': url}

    def parse_and_download(self, share_url, output_dir):
        self.redis_video_error = RedisQueue('video_error_msg:' + share_url)
        cleaned_url = self._clean_and_validate_url(share_url)
        detail_url = self.get_douyin_detail_url(cleaned_url)
        html_content = self.get_douyin_html(detail_url)
        video_id = self.extract_video_id_from_html(html_content)
        video_url = f"{self.PLAY_API_BASE_URL}?{video_id}"
        video_path = self._download_video(video_url, output_dir)
        return {'url': video_url, 'path': video_path}

    def _download_video(self, video_url, output_dir):
        video_name = f"{uuid.uuid4().hex}.mp4"
        video_path = os.path.join(output_dir, video_name)

        response = requests.get(
            video_url,
            timeout=self.DOWNLOAD_TIMEOUT,
            headers=self.headers,
            stream=True
        )
        if response.status_code != self.SUCCESS_STATUS_CODE:
            self.post_video_error_msg(f"下载视频失败: HTTP {response.status_code}")
            raise CustomException(CustomErrors.ERROR_912)

        with open(video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return video_path

    def _clean_and_validate_url(self, share_url):
        if not share_url:
            self.post_video_error_msg("解析失败: 分享链接不能为空")
            raise CustomException(CustomErrors.ERROR_912, msg='分享链接不能为空')

        if 'http://' in share_url:
            cleaned_url = 'http://' + share_url.split('http://', 1)[1]
        elif 'https://' in share_url:
            cleaned_url = 'https://' + share_url.split('https://', 1)[1]
        else:
            self.post_video_error_msg("解析失败: 无效的URL格式")
            raise CustomException(CustomErrors.ERROR_912, msg='无效的URL格式')

        if self.DOUYIN_DOMAIN not in cleaned_url:
            self.post_video_error_msg("解析失败: 暂不支持去除该平台水印")
            raise CustomException(CustomErrors.ERROR_912)

        return cleaned_url

    def get_douyin_detail_url(self, share_url):
        response = requests.head(
            share_url,
            allow_redirects=False,
            timeout=self.HEAD_REQUEST_TIMEOUT,
            headers=self.headers
        )
        if response.status_code not in self.REDIRECT_STATUS_CODES:
            self.post_video_error_msg(f"解析详情页失败: {response.text}")
            raise CustomException(CustomErrors.ERROR_912)

        redirect_url = response.headers.get('Location')
        if not redirect_url:
            self.post_video_error_msg(f"解析详情页失败: {response.text}")
            raise CustomException(CustomErrors.ERROR_912)

        if not redirect_url.startswith('http'):
            redirect_url = f'{self.DOUYIN_BASE_URL}{redirect_url}'

        return redirect_url

    def get_douyin_html(self, detail_url):
        response = requests.get(
            detail_url,
            timeout=self.GET_REQUEST_TIMEOUT,
            headers=self.headers
        )
        if response.status_code != self.SUCCESS_STATUS_CODE:
            self.post_video_error_msg(f"解析详情页失败: {response.text}")
            raise CustomException(CustomErrors.ERROR_912)

        return response.text

    def extract_video_id_from_html(self, html_content):
        video_id = self._extract_video_id_from_lxml(html_content)
        if video_id:
            return video_id

        video_id = self._extract_video_id_from_regex(html_content)
        if video_id:
            return video_id

        raise CustomException(CustomErrors.ERROR_912)

    def _extract_video_id_from_lxml(self, html_content):
        tree = html.fromstring(html_content)

        video_elements = tree.xpath(f'//video[@id="{self.VIDEO_PLAYER_ID}"]')
        html_preview = html_content[:500] if len(html_content) > 500 else html_content
        if not video_elements:
            self.err_msg += f"解析失败: 使用lxml解析HTML未找到id为video-player的video标签 (HTML预览: {html_preview})"
            return None

        src_url = video_elements[0].get('src')
        if not src_url:
            self.err_msg += f"解析失败: 使用lxml解析HTML未找到src属性值 (HTML预览: {html_preview})"
            return None

        parsed_url = urlparse(src_url)
        query_params = parse_qs(parsed_url.query)

        video_id_value = query_params.get(self.VIDEO_ID_PARAM, [None])[0]
        if not video_id_value:
            self.err_msg += f"解析失败: 使用lxml解析HTML未找到video_id (HTML预览: {html_preview})"
            return None

        return f"{self.VIDEO_ID_PARAM}={video_id_value}"

    def _extract_video_id_from_regex(self, html_content):
        pattern = rf'{self.VIDEO_ID_PARAM}=([^&"\]]+)'
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            video_id_value = match.group(1)
            try:
                video_id_value = video_id_value.encode('utf-8').decode('unicode_escape')
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass
            video_id_value = unquote(video_id_value)
            return f"{self.VIDEO_ID_PARAM}={video_id_value}"
        html_preview = html_content[:500] if len(html_content) > 500 else html_content
        self.post_video_error_msg(f"解析失败: 使用正则表达式直接匹配未找到video_id (HTML预览: {html_preview})" + self.err_msg)
        return None
