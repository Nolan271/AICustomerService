"""核心业务 — 对话服务

对话全生命周期管理：
  1. 加载记忆上下文（短/长/偏好）
  2. 调用 LangGraph 工作流
  3. 持久化消息到 SQLite
  4. 提取长期记忆
"""

import json
import logging
import time
from typing import Optional

from app.config import settings
from app.rag.embedder import EmbeddingService
from app.rag.retriever import RAGRetriever
from app.workflows.chat_graph import build_chat_graph
from app.memory.manager import MemoryManager
from app.db.session import async_session_factory
from sqlalchemy import select
from app.models.message import Message, MessageRole
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)


class ChatService:
    """对话服务 —— 集成三层记忆系统"""

    def __init__(
        self,
        retriever: RAGRetriever,
        embedder: EmbeddingService,
    ):
        self.retriever = retriever
        self.embedder = embedder
        self.graph = build_chat_graph()
        self.memory = MemoryManager()

    async def chat(
        self,
        session_id: str,
        user_input: str,
        kb_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_token: Optional[str] = None,       # 外部 API token，数据查询时使用
    ) -> dict:
        """单次对话（非流式）

        流程:
          记忆加载 → LangGraph 工作流 → 持久化 → 长期记忆提取
        """
        start = time.time()

        # 1. 加载记忆上下文
        memory_context = await self.memory.build_context(session_id, user_id)
        history = memory_context["chat_history"]

        # 1b. 快速检测是否为数据查询 — 直通处理（带 token）
        from app.workflows.nodes.data_query_node import data_query_direct, _select_api
        api_check = await _select_api(user_input)
        logger.info("数据查询检测: input=%s, matched=%s", user_input[:30], api_check['path'] if api_check else None)
        dq_result = await data_query_direct(user_input, user_token) if api_check else None
        if dq_result:
            elapsed = (time.time() - start) * 1000
            logger.info("数据查询直通: session=%s, chart=%s, latency=%.0fms",
                         session_id, dq_result.get("chart_config") is not None, elapsed)
            await self._persist_messages(session_id, user_input, dq_result["answer"], {
                "intent": "DATA_QUERY", "user_id": user_id,
                "sources": dq_result.get("sources", []),
            })
            return {
                "answer": dq_result["answer"],
                "sources": dq_result.get("sources", []),
                "follow_up_questions": [],
                "intent": "DATA_QUERY",
                "need_human_handoff": False,
                "handoff_reason": None,
                "memory_summary": memory_context.get("summary", ""),
                "fact_count": len(memory_context.get("long_term_facts", [])),
                "chart_config": dq_result.get("chart_config"),
            }

        # 2. 构建初始状态
        initial_state = {
            "session_id": session_id,
            "user_input": user_input,
            "user_id": user_id or "",
            "user_token": user_token,         # 传给 data_query_node 调外部 API
            "kb_id": kb_id,
            "messages": history,
            "intent": None,
            "retrieved_chunks": None,
            "context_documents": None,
            "answer": None,
            "chart_config": None,
            "sources": None,
            "follow_up_questions": None,
            "need_human_handoff": False,
            "handoff_reason": None,
            "error": None,
            "processing_steps": [],
            "latency_ms": None,
        }

        # 3. 执行 LangGraph 工作流
        try:
            final_state = await self.graph.ainvoke(initial_state)
        except Exception as e:
            logger.exception("对话工作流执行失败")
            final_state = {
                **initial_state,
                "answer": "抱歉，我遇到了技术问题，请稍后再试。",
                "error": str(e),
                "processing_steps": [f"错误: {e}"],
            }

        elapsed = (time.time() - start) * 1000
        logger.info(
            "对话完成: session=%s, intent=%s, chart=%s, latency=%.0fms",
            session_id, final_state.get("intent"),
            final_state.get("chart_config") is not None,
            elapsed,
        )

        # 4. 持久化消息
        await self._persist_messages(
            session_id, user_input, final_state.get("answer", ""),
            final_state,
        )

        # 5. 提取长期记忆
        if user_id:
            try:
                await self.memory.extract_long_term(
                    session_id, user_input,
                    final_state.get("answer", ""), user_id,
                )
            except Exception as e:
                logger.info("长期记忆提取跳过（不影响对话）: %s", e)

        return {
            "answer": final_state.get("answer", ""),
            "sources": final_state.get("sources", []),
            "follow_up_questions": final_state.get("follow_up_questions", []),
            "intent": final_state.get("intent"),
            "need_human_handoff": final_state.get("need_human_handoff", False),
            "handoff_reason": final_state.get("handoff_reason"),
            "memory_summary": memory_context.get("summary", ""),
            "fact_count": len(memory_context.get("long_term_facts", [])),
            "chart_config": final_state.get("chart_config"),
        }

    async def chat_stream(
        self,
        session_id: str,
        user_input: str,
        kb_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """流式对话 — 异步生成器，逐 token 产出

        流程:
          记忆加载 → 意图识别 → 检索 → 流式 LLM 生成 → 持久化 → 记忆提取
        """
        start = time.time()

        # 1. 记忆加载
        memory_context = await self.memory.build_context(session_id, user_id)
        history = memory_context["chat_history"]

        # 2. 意图识别
        from app.llm.factory import LLMFactory
        from app.rag.prompt_templates import INTENT_PROMPT
        import json

        llm = LLMFactory.get_chat_model(temperature=0.0, streaming=False)
        chain = INTENT_PROMPT | llm
        result = await chain.ainvoke({"input": user_input})
        intent = result.content.strip().upper()
        valid_intents = {"KB_QA", "CHITCHAT", "HANDOFF", "CLARIFY"}
        if intent not in valid_intents:
            intent = "KB_QA"

        sources = []
        context_text = ""

        # 3. KB_QA 或 CLARIFY → 检索
        if intent in ("KB_QA", "CLARIFY"):
            from app.rag.retriever import RAGRetriever
            search_results = await self.retriever.retrieve(
                query=user_input, kb_id=kb_id,
            )
            for r in search_results:
                sources.append({
                    "doc_id": r.get("doc_id"),
                    "doc_name": r.get("doc_name", ""),
                    "text": r["text"][:200],
                    "score": round(r.get("score", 0), 4),
                })
            context_parts = [
                f"[{s.get('doc_name', '知识库')}] {r['text']}"
                for r, s in zip(search_results, sources)
            ]
            context_text = "\n\n---\n\n".join(context_parts) if context_parts else ""

        from app.utils.common import format_chat_history
        chat_history = format_chat_history(history)

        # 4. 流式 LLM 生成
        from app.rag.prompt_templates import RAG_PROMPT, CHITCHAT_PROMPT
        stream_llm = LLMFactory.get_chat_model(streaming=True)

        if intent == "CHITCHAT":
            prompt = CHITCHAT_PROMPT.format(
                input=user_input, messages=[], chat_history=chat_history,
            )
        else:
            ctx = context_text or "未找到相关知识。"
            prompt = RAG_PROMPT.format(
                context=ctx, chat_history=chat_history,
                input=user_input, messages=[],
            )

        # 5. 流式输出 token 给前端
        full_answer = ""
        yield {"type": "start", "intent": intent}
        async for chunk in stream_llm.astream(prompt):
            if hasattr(chunk, 'content') and chunk.content:
                token = chunk.content
                full_answer += token
                yield {"type": "token", "data": token}

        # 6. 元数据
        yield {"type": "sources", "data": sources}
        if memory_context.get("long_term_facts"):
            yield {"type": "meta", "fact_count": len(memory_context["long_term_facts"])}

        elapsed = (time.time() - start) * 1000
        logger.info("流式对话完成: session=%s, intent=%s, len=%d, latency=%.0fms",
                     session_id, intent, len(full_answer), elapsed)

        # 7. 持久化
        state = {"intent": intent, "sources": sources,
                 "user_id": user_id, "processing_steps": []}
        await self._persist_messages(session_id, user_input, full_answer, state)

        # 8. 记忆提取
        if user_id:
            try:
                await self.memory.extract_long_term(
                    session_id, user_input, full_answer, user_id,
                )
            except Exception as e:
                logger.info("长期记忆提取跳过（不影响对话）: %s", e)

        yield {"type": "done"}

    async def _persist_messages(
        self,
        session_id: str,
        user_input: str,
        answer: str,
        state: dict,
    ):
        """持久化消息到 SQLite"""
        try:
            async with async_session_factory() as db:
                # 确保 session 存在
                result = await db.execute(
                    select(Conversation).where(Conversation.id == session_id)
                )
                if not result.scalar_one_or_none():
                    conv = Conversation(
                        id=session_id,
                        title=user_input[:100],
                        user_id=state.get("user_id"),
                    )
                    db.add(conv)
                    await db.flush()

                # 保存用户消息
                user_msg = Message(
                    conversation_id=session_id,
                    role=MessageRole.USER,
                    content=user_input,
                )
                db.add(user_msg)

                # 保存 AI 回复 + 元数据
                metadata = {
                    "intent": state.get("intent"),
                    "sources": state.get("sources"),
                    "follow_ups": state.get("follow_up_questions"),
                    "processing_steps": state.get("processing_steps"),
                }
                ai_msg = Message(
                    conversation_id=session_id,
                    role=MessageRole.ASSISTANT,
                    content=answer,
                    metadata_json=json.dumps(metadata, ensure_ascii=False),
                )
                db.add(ai_msg)
                await db.commit()
        except Exception as e:
            logger.warning("消息持久化失败", exc_info=True)
