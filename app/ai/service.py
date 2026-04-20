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


def _call_ai(prompt: str) -> str:
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

    return _call_ai(prompt)


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


def summarize_text(text: str, question: str = "") -> dict:
    try:
        if question:
            prompt = f"""你是一个视频内容分析助手。请根据用户的问题，用简洁易懂的语言回答。

用户问题：{question}

视频转写文本：
{text}

要求：
1. 只用一段话回答，不要分点
2. 语言通俗易懂，不要用大量符号
3. 如果文本中没有相关内容，直接说"视频中没有涉及这个问题"

回答："""
        else:
            prompt = f"""你是一个视频内容总结助手。请用简洁通俗的语言总结以下视频内容。

视频转写文本：
{text}

要求：
1. 总结成2-3段话，每段话简洁明了
2. 说明视频主题是什么
3. 说明视频的核心观点
4. 语言通俗易懂，不要用大量符号列表

总结："""

        summary = _call_ai(prompt)

        return {
            "success": True,
            "summary": summary
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
