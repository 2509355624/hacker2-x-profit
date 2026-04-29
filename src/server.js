const express = require('express');
const multer = require('multer');
const cors = require('cors');
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');
const { spawn } = require('child_process');

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
const tempRefAudioDir = path.join(tempDir, 'ref_audio');
const tempAuxAudioDir = path.join(tempDir, 'aux_audio');
const outputAudioDir = path.join(__dirname, '..', 'output_audio');

if (!fs.existsSync(tempDir)) {
  fs.mkdirSync(tempDir, { recursive: true });
}
if (!fs.existsSync(tempVideoDir)) {
  fs.mkdirSync(tempVideoDir, { recursive: true });
}
if (!fs.existsSync(tempAudioDir)) {
  fs.mkdirSync(tempAudioDir, { recursive: true });
}
if (!fs.existsSync(tempRefAudioDir)) {
  fs.mkdirSync(tempRefAudioDir, { recursive: true });
}
if (!fs.existsSync(tempAuxAudioDir)) {
  fs.mkdirSync(tempAuxAudioDir, { recursive: true });
}
if (!fs.existsSync(outputAudioDir)) {
  fs.mkdirSync(outputAudioDir, { recursive: true });
}

app.use('/output_audio', express.static(outputAudioDir));

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
    const { text, chunk_size = 2000, model = null, custom_config = null } = req.body;

    if (!text) {
      return res.status(400).json({ code: 400, msg: '没有可优化的文本' });
    }

    const result = await optimizeText(text, chunk_size, model, custom_config);

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
    const { text, question = '', model = null, custom_config = null } = req.body;

    if (!text) {
      return res.status(400).json({ code: 400, msg: '没有可总结的文本' });
    }

    const result = await summarizeText(text, question, model, custom_config);

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

app.get('/api/ai_models', (req, res) => {
  const { DEFAULT_MODEL, MODEL_MAPPING } = require('./services/aiService');
  const models = Object.keys(MODEL_MAPPING);
  res.json({
    code: 200,
    data: {
      models: models,
      default: DEFAULT_MODEL
    }
  });
});

const refAudioStorage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, tempRefAudioDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    cb(null, uniqueSuffix + path.extname(file.originalname));
  }
});
const uploadRefAudio = multer({ storage: refAudioStorage });

const auxAudioStorage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, tempAuxAudioDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    cb(null, uniqueSuffix + path.extname(file.originalname));
  }
});
const uploadAuxAudio = multer({ storage: auxAudioStorage });

const audioUploadStorage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, outputAudioDir);
  },
  filename: (req, file, cb) => {
    cb(null, file.originalname);
  }
});
const uploadAudio = multer({ storage: audioUploadStorage });

app.post('/api/upload_ref_audio', uploadRefAudio.single('ref_audio'), (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ code: 400, msg: '请上传参考音频文件' });
    }
    const relativePath = path.relative(path.join(__dirname, '..'), req.file.path);
    res.json({
      code: 200,
      msg: '上传成功',
      data: {
        filename: req.file.filename,
        path: relativePath,
        original_name: req.file.originalname
      }
    });
  } catch (error) {
    console.error(`[Server] upload_ref_audio error: ${error.message}`);
    res.status(500).json({ code: 500, msg: `上传失败：${error.message}` });
  }
});

app.post('/api/upload_aux_audio', uploadAuxAudio.single('aux_audio'), (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ code: 400, msg: '请上传辅助音频文件' });
    }
    const relativePath = path.relative(path.join(__dirname, '..'), req.file.path);
    res.json({
      code: 200,
      msg: '上传成功',
      data: {
        filename: req.file.filename,
        path: relativePath,
        original_name: req.file.originalname
      }
    });
  } catch (error) {
    console.error(`[Server] upload_aux_audio error: ${error.message}`);
    res.status(500).json({ code: 500, msg: `上传失败：${error.message}` });
  }
});

app.post('/api/audio/upload', uploadAudio.array('audio_files'), (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ code: 400, msg: '请上传音频文件' });
    }
    const audioPaths = req.files.map(file => {
      const relativePath = path.relative(path.join(__dirname, '..'), file.path);
      return '/' + relativePath.replace(/\\/g, '/');
    });
    res.json({
      code: 200,
      msg: '上传成功',
      data: {
        audio_paths: audioPaths,
        count: audioPaths.length
      }
    });
  } catch (error) {
    console.error(`[Server] audio/upload error: ${error.message}`);
    res.status(500).json({ code: 500, msg: `上传失败：${error.message}` });
  }
});

app.get('/api/list_ref_audios', (req, res) => {
  try {
    const files = fs.readdirSync(tempRefAudioDir)
      .filter(f => f.endsWith('.wav') || f.endsWith('.mp3') || f.endsWith('.ogg') || f.endsWith('.m4a'))
      .map(f => {
        const filePath = path.join(tempRefAudioDir, f);
        const stats = fs.statSync(filePath);
        return {
          name: f,
          path: path.relative(path.join(__dirname, '..'), filePath).replace(/\\/g, '/'),
          size: stats.size,
          created: stats.birthtime
        };
      });
    res.json({ code: 200, data: files });
  } catch (error) {
    console.error(`[Server] list_ref_audios error: ${error.message}`);
    res.status(500).json({ code: 500, msg: `获取列表失败：${error.message}` });
  }
});

app.get('/api/list_aux_audios', (req, res) => {
  try {
    const files = fs.readdirSync(tempAuxAudioDir)
      .filter(f => f.endsWith('.wav') || f.endsWith('.mp3') || f.endsWith('.ogg') || f.endsWith('.m4a'))
      .map(f => {
        const filePath = path.join(tempAuxAudioDir, f);
        const stats = fs.statSync(filePath);
        return {
          name: f,
          path: path.relative(path.join(__dirname, '..'), filePath).replace(/\\/g, '/'),
          size: stats.size,
          created: stats.birthtime
        };
      });
    res.json({ code: 200, data: files });
  } catch (error) {
    console.error(`[Server] list_aux_audios error: ${error.message}`);
    res.status(500).json({ code: 500, msg: `获取列表失败：${error.message}` });
  }
});

app.post('/api/tts', async (req, res) => {
  try {
    const {
      text,
      ref_audio_path,
      aux_ref_audio_paths = [],
      prompt_text,
      text_lang = '中文',
      prompt_lang = '中文',
      speed_factor = 1,
      sample_steps = 32,
      text_split_method = '不切',
      top_k = 5,
      top_p = 1,
      temperature = 1,
      repetition_penalty = 1.35,
      batch_size = 20,
      ref_text_free = true,
      split_bucket = true,
      fragment_interval = 0.3,
      seed = -1,
      keep_random = true,
      parallel_infer = true,
      super_sampling = false
    } = req.body;

    if (!text) {
      return res.status(400).json({ code: 400, msg: '没有要转换的文本' });
    }
    if (!ref_audio_path) {
      return res.status(400).json({ code: 400, msg: '请选择参考音频' });
    }
    if (!ref_text_free && !prompt_text) {
      return res.status(400).json({ code: 400, msg: '请输入参考音频对应的文本（或勾选不使用参考文本）' });
    }

    const refAudioFullPath = path.join(__dirname, '..', ref_audio_path);
    if (!fs.existsSync(refAudioFullPath)) {
      return res.status(400).json({ code: 400, msg: `参考音频文件不存在: ${ref_audio_path}` });
    }

    const auxAudioFullPaths = [];
    for (const auxPath of aux_ref_audio_paths) {
      const fullPath = path.join(__dirname, '..', auxPath);
      if (fs.existsSync(fullPath)) {
        auxAudioFullPaths.push(fullPath);
      }
    }

    const ttsScript = path.join(__dirname, 'services', 'tts_service.py');
    const pythonBin = process.env.PYTHON_BIN || 'python';

    const params = {
      text_lang,
      aux_ref_audio_paths: auxAudioFullPaths,
      prompt_lang,
      top_k,
      top_p,
      temperature,
      text_split_method,
      batch_size,
      speed_factor,
      ref_text_free,
      split_bucket,
      fragment_interval,
      seed,
      keep_random,
      parallel_infer,
      repetition_penalty,
      sample_steps,
      super_sampling
    };

    const args = [
      ttsScript,
      text,
      refAudioFullPath,
      prompt_text,
      JSON.stringify(params)
    ];

    console.log(`[Server] Calling TTS with ref_audio: ${refAudioFullPath}`);
    console.log(`[Server] aux_ref_audio_paths: ${auxAudioFullPaths.length} files`);

    const result = await new Promise((resolve, reject) => {
      const python = spawn(pythonBin, args);

      let stdout = '';
      let stderr = '';

      python.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      python.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      python.on('close', (code) => {
        if (code === 0) {
          try {
            const result = JSON.parse(stdout.trim());
            resolve(result);
          } catch (e) {
            reject(new Error(`Failed to parse TTS output: ${e.message}\nstdout: ${stdout}`));
          }
        } else {
          reject(new Error(`TTS exited with code ${code}\nstderr: ${stderr}\nstdout: ${stdout}`));
        }
      });

      python.on('error', (err) => {
        reject(err);
      });
    });

    if (result.error) {
      return res.status(500).json({ code: 500, msg: `TTS失败：${result.error}` });
    }

    res.json({
      code: 200,
      msg: '生成成功',
      data: {
        audio_path: result.audio_path,
        temp_audio_path: result.temp_audio_path,
        seed: result.seed
      }
    });
  } catch (error) {
    console.error(`[Server] tts error: ${error.message}`);
    res.status(500).json({ code: 500, msg: `TTS失败：${error.message}` });
  }
});

app.listen(port, () => {
  console.log(`服务器运行在 http://localhost:${port}`);
});

app.post('/api/tts/merge', async (req, res) => {
  try {
    const { audio_paths, output_filename = 'merged_output.wav' } = req.body;

    if (!audio_paths || !Array.isArray(audio_paths) || audio_paths.length === 0) {
      return res.status(400).json({ code: 400, msg: '没有需要合并的音频文件' });
    }

    const ffmpegDir = process.env.FFMPEG_PATH || '';
    const ffmpegPath = ffmpegDir ? path.join(ffmpegDir, 'ffmpeg.exe') : 'ffmpeg';
    const outputDir = path.join(__dirname, '..', 'output_audio');
    const outputPath = path.join(outputDir, output_filename);

    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    const concatListPath = path.join(outputDir, `concat_${Date.now()}.txt`);
    let concatContent = '';
    for (const audioPath of audio_paths) {
      const fullPath = path.join(__dirname, '..', audioPath);
      if (!fs.existsSync(fullPath)) {
        return res.status(400).json({ code: 400, msg: `音频文件不存在: ${audioPath}` });
      }
      concatContent += `file '${fullPath.replace(/\\/g, '/')}'\n`;
    }

    fs.writeFileSync(concatListPath, concatContent);

    const result = await new Promise((resolve, reject) => {
      const args = ['-f', 'concat', '-safe', '0', '-i', concatListPath, '-c', 'copy', outputPath];
      const ffmpeg = spawn(ffmpegPath, args);

      let stderr = '';
      ffmpeg.stderr.on('data', (data) => { stderr += data.toString(); });
      ffmpeg.on('close', (code) => {
        try { fs.unlinkSync(concatListPath); } catch (e) {}
        if (code === 0) {
          resolve({ success: true, output_path: `/output_audio/${output_filename}` });
        } else {
          reject(new Error(`FFmpeg failed with code ${code}: ${stderr}`));
        }
      });
      ffmpeg.on('error', (err) => {
        try { fs.unlinkSync(concatListPath); } catch (e) {}
        reject(err);
      });
    });

    res.json({ code: 200, msg: '合并成功', data: result });
  } catch (error) {
    console.error(`[Server] merge error: ${error.message}`);
    res.status(500).json({ code: 500, msg: `合并失败：${error.message}` });
  }
});

app.get('/api/output_audio/:filename', (req, res) => {
  const filename = req.params.filename;
  const filePath = path.join(__dirname, '..', 'output_audio', filename);
  if (fs.existsSync(filePath)) {
    res.sendFile(filePath);
  } else {
    res.status(404).json({ code: 404, msg: '文件不存在' });
  }
});