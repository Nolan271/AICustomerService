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
        intent_hint: Optional[str] = None,       # 前端分类按钮传入的意图提示
    ) -> dict:
        """单次对话（非流式）

        流程:
          记忆加载 → LangGraph 工作流 → 持久化 → 长期记忆提取
        """
        start = time.time()
        timings = {}

        # 1. 加载记忆上下文
        t0 = time.time()
        memory_context = await self.memory.build_context(session_id, user_id)
        history = memory_context["chat_history"]
        timings["load_memory"] = round((time.time() - t0) * 1000)
        logger.info("[耗时] 加载记忆: %dms", timings["load_memory"])

        # 1b. 快速检测是否为数据查询 — 直通处理（带 token）
        t0 = time.time()
        from app.workflows.nodes.data_query_node import data_query_direct, _select_api
        api_check = await _select_api(user_input)
        timings["detect_intent"] = round((time.time() - t0) * 1000)
        logger.info("[耗时] 数据查询检测: %dms, matched=%s",
                     timings["detect_intent"], api_check['path'] if api_check else None)
        dq_result = await data_query_direct(user_input, user_token) if api_check else None
        if dq_result:
            elapsed = round((time.time() - start) * 1000)
            logger.info("[耗时] 数据查询直通: %dms | session=%s, chart=%s",
                         elapsed, session_id, dq_result.get("chart_config") is not None)
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
                "timings": timings,
            }

        # 2. 构建初始状态
        initial_state = {
            "session_id": session_id,
            "user_input": user_input,
            "user_id": user_id or "",
            "user_token": user_token,         # 传给 data_query_node 调外部 API
            "kb_id": kb_id,
            "intent_hint": intent_hint,         # 传给 router_node 加速分类
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

        # 3. 执行 LangGraph 工作流（包含 意图识别→检索/数据查询→生成→护栏→记忆）
        t0 = time.time()
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
        timings["workflow"] = round((time.time() - t0) * 1000)

        # ← 解析工作流各步骤耗时
        steps = final_state.get("processing_steps", [])
        logger.info("[耗时] 工作流总耗时: %dms | 步骤: %s",
                     timings["workflow"], " → ".join(s for s in steps if s))

        # 4. 持久化消息
        t0 = time.time()
        await self._persist_messages(
            session_id, user_input, final_state.get("answer", ""),
            final_state,
        )
        timings["persist"] = round((time.time() - t0) * 1000)

        elapsed = round((time.time() - start) * 1000)
        logger.info(
            "[耗时] ====== 总耗时: %dms ====== \n"
            "  加载记忆: %dms | 检测: %dms | 工作流: %dms | 持久化: %dms\n"
            "  session=%s | intent=%s",
            elapsed,
            timings.get("load_memory", 0),
            timings.get("detect_intent", 0),
            timings["workflow"],
            timings["persist"],
            session_id, final_state.get("intent"),
        )

        # 5. 提取长期记忆（暂时注释以提升速度）
        # if user_id:
        #     try:
        #         await self.memory.extract_long_term(
        #             session_id, user_input,
        #             final_state.get("answer", ""), user_id,
        #         )
        #     except Exception as e:
        #         logger.info("长期记忆提取跳过（不影响对话）: %s", e)

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

        llm = LLMFactory.get_fast_model(temperature=0.0, streaming=False)
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
        stream_llm = LLMFactory.get_fast_model(streaming=True)

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

        # 8. 记忆提取（暂时注释以提升速度）
        # if user_id:
        #     try:
        #         await self.memory.extract_long_term(
        #             session_id, user_input, full_answer, user_id,
        #         )
        #     except Exception as e:
        #         logger.info("长期记忆提取跳过（不影响对话）: %s", e)

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
