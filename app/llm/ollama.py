"""Ollama 专用配置 — 本地 LLM 推理"""

from langchain_ollama import ChatOllama

from app.config import settings


def create_ollama_chat(
    model: str | None = None,
    temperature: float = 0.3,
    streaming: bool = True,
) -> ChatOllama:
    return ChatOllama(
        model=model or settings.OLLAMA_MODEL,
        temperature=temperature,
        streaming=streaming,
        base_url=settings.OLLAMA_BASE_URL,
    )
