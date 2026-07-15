"""LLM 工厂 — 根据配置动态创建 LLM 实例，支持多后端切换"""

import logging
from typing import Optional

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from app.config import settings

logger = logging.getLogger(__name__)


class LLMFactory:
    """LLM 实例工厂，支持 openai / ollama / anthropic + 分层模型"""

    @classmethod
    def get_fast_model(
        cls,
        temperature: Optional[float] = None,
        streaming: Optional[bool] = None,
    ) -> BaseChatModel:
        """获取快速模型（qwen-turbo），用于意图识别等简单任务"""
        provider = settings.LLM_PROVIDER
        model = settings.FAST_LLM_MODEL
        temp = temperature if temperature is not None else 0.0
        stream = streaming if streaming is not None else False

        if provider == "openai":
            return init_chat_model(
                model,
                model_provider="openai",
                temperature=temp,
                streaming=stream,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
        # ollama/anthropic 降级为默认模型
        return cls.get_chat_model(temperature=temp, streaming=stream)

    @classmethod
    def get_chat_model(
        cls,
        temperature: Optional[float] = None,
        streaming: Optional[bool] = None,
        model_name: Optional[str] = None,
    ) -> BaseChatModel:
        """获取聊天模型实例

        Args:
            temperature: 温度参数，默认使用 settings.TEMPERATURE
            streaming: 是否流式输出，默认使用 settings.STREAMING
            model_name: 模型名称，默认使用 settings 中对应的模型
        """
        temp = temperature if temperature is not None else settings.TEMPERATURE
        stream = streaming if streaming is not None else settings.STREAMING

        provider = settings.LLM_PROVIDER
        logger.debug("创建 LLM: provider=%s, model=%s", provider, model_name or "default")

        if provider == "openai":
            model = model_name or settings.OPENAI_MODEL
            return init_chat_model(
                model,
                model_provider="openai",
                temperature=temp,
                streaming=stream,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )

        elif provider == "ollama":
            model = model_name or settings.OLLAMA_MODEL
            return init_chat_model(
                model,
                model_provider="ollama",
                temperature=temp,
                streaming=stream,
                base_url=settings.OLLAMA_BASE_URL,
            )

        elif provider == "anthropic":
            return init_chat_model(
                "claude-sonnet-5-20251001",
                model_provider="anthropic",
                temperature=temp,
                streaming=stream,
            )

        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")
