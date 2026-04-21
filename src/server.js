const express = require('express');
const multer = require('multer');
const cors = require('cors');
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');

dotenv.config({ path: path.join(__dirname, '..', '.env') });

const app = express();
const port = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use(express.static(path.join(__dirname, '..', 'public')));

const tempDir = path.join(__dirname, '..', 'temp');
const tempVideoDir = path.join(tempDir, 'video');
const tempAudioDir = path.join(tempDir, 'audio');

if (!fs.existsSync(tempDir)) {
  fs.mkdirSync(tempDir, { recursive: true });
}
if (!fs.existsSync(tempVideoDir)) {
  fs.mkdirSync(tempVideoDir, { recursive: true });
}
if (!fs.existsSync(tempAudioDir)) {
  fs.mkdirSync(tempAudioDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, tempVideoDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = uuidv4() + path.extname(file.originalname);
    cb(null, uniqueSuffix);
  }
});

const upload = multer({ storage });

app.get('/', (req, res) => {
  res.send('视频转文本服务');
});

const videoToText = require('./services/videoToText');
const { parseDouyinVideo } = require('./services/douyinParser');
const { optimizeText, summarizeText } = require('./services/aiService');

app.post('/api/video2text', upload.single('video'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ code: 400, msg: '请上传视频文件' });
    }

    const videoPath = req.file.path;
    const simplified = req.body.simplified !== 'false';

    console.log(`[Server] Processing uploaded video: ${videoPath}`);

    const result = await videoToText(videoPath, simplified);

    fs.unlinkSync(videoPath);

    res.json({ code: 200, msg: '转写成功', data: result });
  } catch (error) {
    console.error(`[Server] video2text error: ${error.message}`);
    res.status(500).json({ code: 500, msg: `失败：${error.message}` });
  }
});

app.post('/api/parse_douyin', async (req, res) => {
  let videoPath = null;
  try {
    const { url, simplified = true } = req.body;

    if (!url) {
      return res.status(400).json({ code: 400, msg: '请提供抖音分享链接' });
    }

    console.log(`[Server] Parsing Douyin URL: ${url}`);

    const { path: downloadedPath, url: videoUrl } = await parseDouyinVideo(url, tempVideoDir);
    videoPath = downloadedPath;

    console.log(`[Server] Video downloaded, processing...`);

    const transcription = await videoToText(videoPath, simplified);

    fs.unlinkSync(videoPath);

    const result = {
      video_url: videoUrl,
      transcription
    };

    res.json({ code: 200, msg: '解析并转写成功', data: result });
  } catch (error) {
    console.error(`[Server] parse_douyin error: ${error.message}`);
    if (videoPath && fs.existsSync(videoPath)) {
      fs.unlinkSync(videoPath);
    }
    res.status(500).json({ code: 500, msg: `解析失败：${error.message}` });
  }
});

app.post('/api/optimize_text', async (req, res) => {
  try {
    const { text, chunk_size = 2000 } = req.body;

    if (!text) {
      return res.status(400).json({ code: 400, msg: '没有可优化的文本' });
    }

    const result = await optimizeText(text, chunk_size);

    if (result.success) {
      res.json({ code: 200, msg: '优化成功', data: result });
    } else {
      res.status(500).json({ code: 500, msg: `优化失败：${result.error}` });
    }
  } catch (error) {
    console.error(`[Server] optimize_text error: ${error.message}`);
    res.status(500).json({ code: 500, msg: `优化失败：${error.message}` });
  }
});

app.post('/api/summarize_text', async (req, res) => {
  try {
    const { text, question = '' } = req.body;

    if (!text) {
      return res.status(400).json({ code: 400, msg: '没有可总结的文本' });
    }

    const result = await summarizeText(text, question);

    if (result.success) {
      res.json({ code: 200, msg: '总结成功', data: result });
    } else {
      res.status(500).json({ code: 500, msg: `总结失败：${result.error}` });
    }
  } catch (error) {
    console.error(`[Server] summarize_text error: ${error.message}`);
    res.status(500).json({ code: 500, msg: `总结失败：${error.message}` });
  }
});

app.listen(port, () => {
  console.log(`服务器运行在 http://localhost:${port}`);
});