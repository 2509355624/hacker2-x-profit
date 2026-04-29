const { OpenAI } = require('openai');

const openai = new OpenAI({
  apiKey: process.env.VOLCANO_API_KEY,
  baseURL: process.env.VOLCANO_BASE_URL
});

let MODEL_MAPPING = {};
try {
  MODEL_MAPPING = JSON.parse(process.env.MODEL_MAPPING || '{}');
} catch (e) {
  console.error('Failed to parse MODEL_MAPPING from env:', e.message);
}

const DEFAULT_MODEL = process.env.AI_MODEL || null;

function getModelId(modelName) {
  const mapping = MODEL_MAPPING[modelName];
  if (mapping && mapping.model) {
    return mapping.model;
  }
  return modelName;
}

function createCustomClient(customConfig) {
  return new OpenAI({
    apiKey: customConfig.api_key,
    baseURL: customConfig.base_url
  });
}

function splitText(text, chunkSize = 2000) {
  const sentences = text.split(/([。！？\n]+)/);
  const chunks = [];
  let currentChunk = "";

  for (let i = 0; i < sentences.length - 1; i += 2) {
    const sentence = sentences[i] + sentences[i + 1];
    if (currentChunk.length + sentence.length <= chunkSize) {
      currentChunk += sentence;
    } else {
      if (currentChunk) {
        chunks.push(currentChunk.trim());
      }
      currentChunk = sentence;
    }
  }

  if (sentences[sentences.length - 1] && currentChunk.length + sentences[sentences.length - 1].length <= chunkSize) {
    currentChunk += sentences[sentences.length - 1];
  }

  if (currentChunk.trim()) {
    chunks.push(currentChunk.trim());
  }

  return chunks.length > 0 ? chunks : [text];
}

async function callAI(prompt, modelName = null, customConfig = null) {
  let client = openai;
  let modelId;

  if (customConfig) {
    client = createCustomClient(customConfig);
    modelId = customConfig.model;
  } else {
    modelId = getModelId(modelName || DEFAULT_MODEL);
  }

  const response = await client.chat.completions.create({
    model: modelId,
    messages: [{ role: "user", content: prompt }],
    temperature: 0
  });

  return response.choices[0].message.content.trim();
}

async function optimizeChunk(chunk, modelName, customConfig) {
  const prompt = `你是一个专业的语音识别文本优化助手。以下文本是从视频/音频中通过AI语音识别得到的，可能存在同音字错误、简繁体混杂、标点错误、多行分段格式混乱等问题。

请对以下文本进行优化：
1. 修正明显的同音字错误
2. 统一简繁体（全部转为简体）
3. 修正明显的错别字
4. 将原本分行的诗歌/歌词格式转换为连续段落格式，用恰当的标点符号（，。；：）分隔句子
5. 保持原文的语义和风格不变
6. 只输出优化后的文本内容，不要任何解释、备注或引用格式

原文：
${chunk}

优化后（连续段落格式）：`;

  return callAI(prompt, modelName, customConfig);
}

async function optimizeText(text, chunkSize = 2000, modelName = null, customConfig = null) {
  try {
    if (text.length <= chunkSize) {
      const optimized = await optimizeChunk(text, modelName, customConfig);
      return {
        success: true,
        optimized_text: optimized,
        chunks: 1
      };
    }

    const chunks = splitText(text, chunkSize);
    const optimizedChunks = [];

    for (let i = 0; i < chunks.length; i++) {
      try {
        const optimized = await optimizeChunk(chunks[i], modelName, customConfig);
        optimizedChunks.push(optimized);
      } catch (error) {
        return {
          success: false,
          error: `处理第${i + 1}块时出错: ${error.message}`,
          chunks_processed: i,
          total_chunks: chunks.length
        };
      }
    }

    const fullOptimized = optimizedChunks.join('');

    return {
      success: true,
      optimized_text: fullOptimized,
      chunks: chunks.length
    };
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

async function summarizeText(text, question = "", modelName = null, customConfig = null) {
  try {
    let prompt;

    if (question) {
      prompt = `你是一个视频内容分析助手。请根据用户的问题，用简洁易懂的语言回答。

用户问题：${question}

视频转写文本：
${text}

要求：
1. 只用一段话回答，不要分点
2. 语言通俗易懂，不要用大量符号
3. 如果文本中没有相关内容，直接说"视频中没有涉及这个问题"

回答：`;
    } else {
      prompt = `你是一个视频内容总结助手。请用简洁通俗的语言总结以下视频内容。

视频转写文本：
${text}

要求：
1. 总结成2-3段话，每段话简洁明了
2. 说明视频主题是什么
3. 说明视频的核心观点
4. 语言通俗易懂，不要用大量符号列表

总结：`;
    }

    const summary = await callAI(prompt, modelName, customConfig);

    return {
      success: true,
      summary
    };
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

module.exports = {
  optimizeText,
  summarizeText,
  DEFAULT_MODEL,
  MODEL_MAPPING
};