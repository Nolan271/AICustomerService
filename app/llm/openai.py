"""OpenAI 专用配置 — 如需更细粒度的 OpenAI 控制"""

from langchain_openai import ChatOpenAI

from app.config import settings


def create_openai_chat(
    model: str | None = None,
    temperature: float = 0.3,
    streaming: bool = True,
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model or settings.OPENAI_MODEL,
        temperature=temperature,
        streaming=streaming,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )
