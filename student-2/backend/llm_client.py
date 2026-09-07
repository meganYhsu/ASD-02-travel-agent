import os
import requests


OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://ollama:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:0.5b"
)


def create_chat_completion(
    messages,
    max_tokens=200,
    temperature=0.2,
    model=None
):
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": model or OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        },
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    return data["message"]["content"]