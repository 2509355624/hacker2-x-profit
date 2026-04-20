import re
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from .config import AIConfig

_executor = ThreadPoolExecutor(max_workers=4)


def _split_text(text: str, chunk_size: int = 2000) -> list:
    sentences = re.split(r'([。！？\n]+)', text)
    chunks = []
    current_chunk = ""

    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i] + sentences[i + 1]
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence

    if sentences[-1] and len(current_chunk) + len(sentences[-1]) <= chunk_size:
        current_chunk += sentences[-1]

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text]


def _optimize_chunk(chunk: str) -> str:
    prompt = f"""你是一个专业的语音识别文本优化助手。以下文本是从视频/音频中通过AI语音识别得到的，可能存在同音字错误、简繁体混杂、标点错误等问题。

请对以下文本进行优化：
1. 修正明显的同音字错误
2. 统一简繁体（全部转为简体）
3. 修正明显的错别字
4. 修正标点符号
5. 保持原文的语义和风格不变

只返回优化后的文本，不要任何解释或备注。

原文：
{chunk}

优化后："""

    model_config = AIConfig.get_model_config()
    parameters = AIConfig.get_model_parameters()

    client = OpenAI(
        api_key=model_config['api_key'],
        base_url=model_config['base_url']
    )

    response = client.chat.completions.create(
        model=model_config['model'],
        messages=[{"role": "user", "content": prompt}],
        temperature=parameters['temperature']
    )

    return response.choices[0].message.content.strip()


def optimize_text(text: str, chunk_size: int = 2000) -> dict:
    try:
        if len(text) <= chunk_size:
            optimized = _optimize_chunk(text)
            return {
                "success": True,
                "optimized_text": optimized,
                "chunks": 1
            }

        chunks = _split_text(text, chunk_size)
        optimized_chunks = []

        for i, chunk in enumerate(chunks):
            try:
                optimized = _optimize_chunk(chunk)
                optimized_chunks.append(optimized)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"处理第{i + 1}块时出错: {str(e)}",
                    "chunks_processed": i,
                    "total_chunks": len(chunks)
                }

        full_optimized = "".join(optimized_chunks)

        return {
            "success": True,
            "optimized_text": full_optimized,
            "chunks": len(chunks)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
