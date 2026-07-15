"""
记忆管理器 — 三层记忆体系

使用方式:
  manager = MemoryManager()
  await manager.remember_short_term(session_id, role, content)
  facts = await manager.extract_long_term(session_id, user_input, answer)
  await manager.save_preference(user_id, 'answer_style', 'concise')
  context = await manager.build_context(session_id, user_id)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, desc, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import async_session_factory
from app.models.memory import MemoryFact, UserPreference
from app.models.message import Message
from app.utils.common import generate_uuid

logger = logging.getLogger(__name__)


class MemoryManager:
    """三层记忆管理器"""

    # ── 短期记忆 (当前对话上下文) ──────────────────────────────────

    async def get_short_term(
        self, session_id: str, limit: int = 10
    ) -> list[dict]:
        """获取短期记忆 = 最近 N 轮对话"""
        async with async_session_factory() as db:
            result = await db.execute(
                select(Message)
                .where(Message.conversation_id == session_id)
                .order_by(Message.created_at.desc())
                .limit(limit * 2)
            )
            messages = list(reversed(result.scalars().all()))
            return [
                {"role": m.role, "content": m.content}
                for m in messages
            ]

    async def summarize_short_term(self, session_id: str) -> str:
        """对短期记忆做摘要（压缩上下文）"""
        messages = await self.get_short_term(session_id, limit=20)
        if len(messages) <= 20:  # 少于 10 轮对话不做摘要
            return ""

        from app.llm.factory import LLMFactory
        from app.rag.prompt_templates import SUMMARY_PROMPT

        dialog = "\n".join(
            f"{m['role']}: {m['content'][:200]}"
            for m in messages[:-4]  # 最近两轮不压缩
        )
        llm = LLMFactory.get_fast_model()  # 用快模型
        result = await llm.ainvoke(
            SUMMARY_PROMPT.format(dialog=dialog)
        )
        return result.content

    # ── 长期记忆 (事实提取) ────────────────────────────────────────

    async def extract_long_term(
        self,
        session_id: str,
        user_input: str,
        answer: str,
        user_id: Optional[str] = None,
    ) -> list[MemoryFact]:
        """从一次对话中提取长期记忆

        使用 LLM 分析对话内容，提取可作为记忆的事实。
        """
        if not user_id:
            return []

        from app.llm.factory import LLMFactory
        from langchain_core.prompts import ChatPromptTemplate

        extract_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """从客服对话中提取可作为长期记忆的信息。
返回 JSON 数组格式，每条包含:
  - type: product(产品信息) | requirement(用户需求) | preference(偏好) | general(通用)
  - content: 记忆内容（简洁的一句话）
  - keywords: 关键词（逗号分隔）

如果没有需要记忆的信息，返回 []。只返回 JSON，不要其他文字。""",
            ),
            ("human", "用户: {input}\n客服: {answer}"),
        ])

        llm = LLMFactory.get_chat_model(temperature=0.0, streaming=False)
        try:
            result = await llm.ainvoke(
                extract_prompt.format(input=user_input, answer=answer)
            )
            facts_data = json.loads(result.content.strip())
        except Exception as e:
            logger.warning("记忆提取失败（不影响对话继续）", exc_info=True)
            return []

        saved = []
        async with async_session_factory() as db:
            for fact in facts_data:
                mf = MemoryFact(
                    user_id=user_id,
                    session_id=session_id,
                    fact_type=fact.get("type", "general"),
                    content=fact.get("content", ""),
                    keywords=fact.get("keywords", ""),
                    confidence=0.7,
                    source="ai_inferred",
                )
                db.add(mf)
                saved.append(mf)
            if saved:
                await db.commit()
                logger.info("提取 %d 条长期记忆", len(saved))
        return saved

    async def get_long_term(
        self, user_id: str, fact_type: Optional[str] = None, limit: int = 20
    ) -> list[MemoryFact]:
        """获取用户的长期记忆"""
        async with async_session_factory() as db:
            stmt = (
                select(MemoryFact)
                .where(MemoryFact.user_id == user_id)
                .order_by(MemoryFact.last_accessed_at.desc().nullslast(),
                          MemoryFact.confidence.desc())
                .limit(limit)
            )
            if fact_type:
                stmt = stmt.where(MemoryFact.fact_type == fact_type)
            result = await db.execute(stmt)
            facts = list(result.scalars().all())

            # 更新访问时间
            for f in facts:
                f.last_accessed_at = datetime.now(timezone.utc)
                f.access_count += 1
            if facts:
                await db.commit()
        return facts

    # ── 偏好记忆 ──────────────────────────────────────────────────

    async def save_preference(
        self, user_id: str, key: str, value: str
    ) -> UserPreference:
        """保存用户偏好"""
        async with async_session_factory() as db:
            result = await db.execute(
                select(UserPreference).where(
                    UserPreference.user_id == user_id,
                    UserPreference.pref_key == key,
                )
            )
            pref = result.scalar_one_or_none()
            if pref:
                pref.pref_value = value
            else:
                pref = UserPreference(
                    user_id=user_id, pref_key=key, pref_value=value
                )
                db.add(pref)
            await db.commit()
            await db.refresh(pref)
        return pref

    async def get_preference(
        self, user_id: str, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """获取用户偏好"""
        async with async_session_factory() as db:
            result = await db.execute(
                select(UserPreference).where(
                    UserPreference.user_id == user_id,
                    UserPreference.pref_key == key,
                )
            )
            pref = result.scalar_one_or_none()
        return pref.pref_value if pref else default

    async def get_all_preferences(self, user_id: str) -> dict:
        """获取用户所有偏好"""
        async with async_session_factory() as db:
            result = await db.execute(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            return {p.pref_key: json.loads(p.pref_value) for p in result.scalars().all()}

    # ── 构建上下文 ────────────────────────────────────────────────

    async def build_context(
        self,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """为 LLM 构建完整的记忆上下文

        Returns:
            {
                "chat_history": [...],    # 短期记忆
                "summary": "...",          # 历史摘要（长对话时）
                "long_term_facts": [...],  # 长期记忆
                "preferences": {...},      # 偏好记忆
            }
        """
        context = {"chat_history": [], "summary": "", "long_term_facts": [], "preferences": {}}

        # 短期记忆
        context["chat_history"] = await self.get_short_term(session_id)
        # 对话摘要已关闭（单轮对话，无需压缩历史）
        # if len(context["chat_history"]) > 20:
        #     context["summary"] = await self.summarize_short_term(session_id)

        # 长期记忆
        if user_id:
            facts = await self.get_long_term(user_id)
            context["long_term_facts"] = [
                {"type": f.fact_type, "content": f.content, "confidence": f.confidence}
                for f in facts
            ]
            context["preferences"] = await self.get_all_preferences(user_id)

        return context
