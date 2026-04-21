const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { v4: uuidv4 } = require('uuid');

function extractAudio(videoPath, outputDir) {
  return new Promise((resolve, reject) => {
    const audioName = `${uuidv4()}.wav`;
    const audioPath = path.join(outputDir, audioName);

    const ffmpegBin = process.env.FFMPEG_PATH
      ? path.join(process.env.FFMPEG_PATH, 'ffmpeg.exe')
      : 'ffmpeg';

    const args = [
      '-i', videoPath,
      '-vn',
      '-acodec', 'pcm_s16le',
      '-ac', '1',
      '-ar', '16000',
      '-f', 'wav',
      '-y',
      audioPath
    ];

    const ffmpeg = spawn(ffmpegBin, args);

    let stderr = '';

    ffmpeg.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        resolve(audioPath);
      } else {
        reject(new Error(`ffmpeg exited with code ${code}\n${stderr}`));
      }
    });

    ffmpeg.on('error', (err) => {
      reject(err);
    });
  });
}

function transcribeWithWhisper(audioPath, convertToSimplified) {
  return new Promise((resolve, reject) => {
    const pythonScript = path.join(__dirname, 'whisper_service.py');
    const pythonBin = process.env.PYTHON_BIN || 'python';

    const args = [pythonScript, audioPath, convertToSimplified.toString()];

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
          const result = JSON.parse(stdout);
          resolve(result);
        } catch (e) {
          reject(new Error(`Failed to parse Whisper output: ${e.message}`));
        }
      } else {
        reject(new Error(`Whisper exited with code ${code}`));
      }
    });

    python.on('error', (err) => {
      reject(err);
    });
  });
}

async function videoToText(videoPath, convertToSimplified = false) {
  const tempAudioDir = path.join(__dirname, '..', '..', 'temp', 'audio');

  if (!fs.existsSync(tempAudioDir)) {
    fs.mkdirSync(tempAudioDir, { recursive: true });
  }

  const audioPath = await extractAudio(videoPath, tempAudioDir);

  try {
    const result = await transcribeWithWhisper(audioPath, convertToSimplified);

    const fullText = result.full_text || '';
    const segments = result.segments || [];
    const srtContent = result.srt_content || '';

    return {
      full_text: fullText,
      srt_content: srtContent,
      segments
    };
  } finally {
    if (fs.existsSync(audioPath)) {
      fs.unlinkSync(audioPath);
    }
  }
}

module.exports = videoToText;