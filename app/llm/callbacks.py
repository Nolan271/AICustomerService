"""LangChain Callbacks — 监控、日志、Token 计数"""

import logging
from typing import Any, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


class TokenCounterCallback(BaseCallbackHandler):
    """追踪 LLM 调用的 Token 消耗"""

    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        logger.debug("LLM 调用开始: %s", prompts[0][:100])

    def on_llm_end(self, response, **kwargs: Any) -> None:
        if hasattr(response, "llm_output") and response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            self.prompt_tokens += token_usage.get("prompt_tokens", 0)
            self.completion_tokens += token_usage.get("completion_tokens", 0)
            logger.info(
                "Token 使用: prompt=%d, completion=%d, total=%d",
                token_usage.get("prompt_tokens", 0),
                token_usage.get("completion_tokens", 0),
                token_usage.get("total_tokens", 0),
            )

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class StreamingCallback(BaseCallbackHandler):
    """流式输出回调 — 用于 SSE 推送"""

    def __init__(self):
        self.tokens: list[str] = []

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self.tokens.append(token)
