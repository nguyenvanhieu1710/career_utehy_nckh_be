import os
import json
import requests
import logging
from typing import Generator

logger = logging.getLogger(__name__)

# Ollama configuration from environment
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))


def generate_answer(prompt: str) -> str:
    """
    Generate answer from Ollama LLM
    
    Args:
        prompt: User question/prompt
        
    Returns:
        Generated answer or error message
    """
    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }
        
        logger.info(f"🤖 Calling Ollama model: {MODEL_NAME}")
        response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        
        if response.status_code != 200:
            logger.error(f"❌ Ollama error: {response.status_code} - {response.text}")
            return "Xin lỗi, hệ thống AI đang gặp sự cố. Vui lòng thử lại sau."
        
        data = response.json()
        answer = data.get("response", "").strip()
        
        if not answer:
            logger.warning("⚠️ Ollama returned empty response")
            return "Xin lỗi, tôi không thể tạo câu trả lời. Vui lòng thử lại."
        
        logger.info(f"✅ Generated answer: {len(answer)} characters")
        return answer
        
    except requests.exceptions.ConnectionError:
        logger.error("❌ Cannot connect to Ollama - Is it running?")
        return "Không thể kết nối đến hệ thống AI. Vui lòng kiểm tra Ollama đã chạy chưa."
    
    except requests.exceptions.Timeout:
        logger.error(f"❌ Ollama timeout after {OLLAMA_TIMEOUT}s")
        return "Yêu cầu xử lý quá lâu. Vui lòng thử câu hỏi ngắn gọn hơn."
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}", exc_info=True)
        return "Đã xảy ra lỗi không mong muốn. Vui lòng thử lại sau."

def stream_answer(prompt: str) -> Generator[str, None, None]:
    """
    Generate answer from Ollama LLM (streaming)
    Yields partial text chunks
    """
    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": True
        }

        logger.info(f"🤖 Calling Ollama model (streaming): {MODEL_NAME}")

        with requests.post(
            OLLAMA_URL,
            json=payload,
            stream=True,
            timeout=OLLAMA_TIMEOUT
        ) as response:

            if response.status_code != 200:
                logger.error(f"❌ Ollama stream error: {response.status_code}")
                yield "Xin lỗi, hệ thống AI đang gặp sự cố."
                return

            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    data = json.loads(line.decode("utf-8"))

                    if "response" in data:
                        yield data["response"]

                    if data.get("done"):
                        logger.info("✅ Streaming completed")
                        break

                except json.JSONDecodeError:
                    logger.warning("⚠️ Failed to decode Ollama stream chunk")

    except requests.exceptions.ConnectionError:
        logger.error("❌ Cannot connect to Ollama (stream)")
        yield "Không thể kết nối đến hệ thống AI."

    except requests.exceptions.Timeout:
        logger.error(f"❌ Ollama stream timeout after {OLLAMA_TIMEOUT}s")
        yield "Yêu cầu xử lý quá lâu."

    except Exception as e:
        logger.error(f"❌ Streaming unexpected error: {str(e)}", exc_info=True)
        yield "Đã xảy ra lỗi không mong muốn."