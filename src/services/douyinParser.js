const axios = require('axios');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const DOUYIN_BASE_URL = 'https://www.douyin.com';
const PLAY_API_BASE_URL = 'https://www.iesdouyin.com/aweme/v1/play/';

const headers = {
  'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
  'Referer': DOUYIN_BASE_URL + '/'
};

function extractUrl(text) {
  const urlPattern = /https?:\/\/v\.douyin\.com\/[^\s]+/;
  const match = text.match(urlPattern);
  if (match) {
    return match[0].replace(/[^\S]+$/, '');
  }
  return text.trim();
}

async function cleanAndValidateUrl(shareUrl) {
  if (!shareUrl) {
    throw new Error('分享链接不能为空');
  }

  let cleanedUrl = shareUrl;
  if (shareUrl.includes('http://')) {
    const parts = shareUrl.split('http://');
    cleanedUrl = 'http://' + parts[1];
  } else if (shareUrl.includes('https://')) {
    const parts = shareUrl.split('https://');
    cleanedUrl = 'https://' + parts[1];
  }

  if (!cleanedUrl.includes('douyin.com')) {
    throw new Error('暂不支持去除该平台水印');
  }

  return cleanedUrl;
}

async function getDouyinDetailUrl(shareUrl) {
  try {
    const response = await axios.head(shareUrl, {
      headers,
      maxRedirects: 0,
      timeout: 5000
    });

    if (response.status === 301 || response.status === 302 || response.status === 307 || response.status === 308) {
      let redirectUrl = response.headers.location;
      if (!redirectUrl.startsWith('http')) {
        redirectUrl = DOUYIN_BASE_URL + redirectUrl;
      }
      return redirectUrl;
    }
  } catch (error) {
    if (error.response && error.response.status === 301 || error.response?.status === 302) {
      let redirectUrl = error.response.headers.location;
      if (!redirectUrl.startsWith('http')) {
        redirectUrl = DOUYIN_BASE_URL + redirectUrl;
      }
      return redirectUrl;
    }
  }

  throw new Error('解析详情页失败');
}

async function getDouyinHtml(detailUrl) {
  const response = await axios.get(detailUrl, {
    headers,
    timeout: 8000
  });
  return response.data;
}

function extractVideoId(htmlContent) {
  const patterns = [
    /video_id=([^&"\]]+)/,
    /"video_id":"([^"]+)"/,
    /RENDER_DATA=([^&]+)/
  ];

  for (const pattern of patterns) {
    const match = htmlContent.match(pattern);
    if (match) {
      let videoId = match[1];
      try {
        videoId = Buffer.from(videoId, 'utf-8').toString('unicode_escape');
      } catch (e) {}
      return `video_id=${decodeURIComponent(videoId)}`;
    }
  }

  return null;
}

async function downloadVideo(videoUrl, outputDir) {
  const videoName = `${uuidv4()}.mp4`;
  const videoPath = path.join(outputDir, videoName);

  const response = await axios.get(videoUrl, {
    headers,
    responseType: 'stream',
    timeout: 60000
  });

  const writer = fs.createWriteStream(videoPath);

  response.data.pipe(writer);

  return new Promise((resolve, reject) => {
    writer.on('finish', () => {
      resolve(videoPath);
    });
    writer.on('error', reject);
  });
}

async function parseDouyinVideo(shareUrl, outputDir) {
  const extractedUrl = extractUrl(shareUrl);
  const cleanedUrl = await cleanAndValidateUrl(extractedUrl);
  const detailUrl = await getDouyinDetailUrl(cleanedUrl);
  const htmlContent = await getDouyinHtml(detailUrl);
  const videoId = extractVideoId(htmlContent);

  if (!videoId) {
    throw new Error('解析失败: 未找到video_id');
  }

  const videoUrl = `${PLAY_API_BASE_URL}?${videoId}`;
  const videoPath = await downloadVideo(videoUrl, outputDir);

  return { url: videoUrl, path: videoPath };
}

module.exports = { parseDouyinVideo };