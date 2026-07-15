"""LangGraph 节点 — 意图路由

分析用户输入，判断意图类型：
- KB_QA: 知识问答 → 走检索 + 生成
- DATA_QUERY: 数据查询（营收/订单/电量等）→ 调外部 API
- CHITCHAT: 闲聊问候 → 直接生成
- HANDOFF: 转人工 → 返回转人工提示
- CLARIFY: 追问澄清 → 结合上下文检索
"""

from app.llm.factory import LLMFactory
from app.rag.prompt_templates import INTENT_PROMPT
from app.workflows.state import ChatState


async def router_node(state: ChatState) -> dict:
    """意图识别节点"""
    llm = LLMFactory.get_chat_model(temperature=0.0, streaming=False)
    chain = INTENT_PROMPT | llm

    result = await chain.ainvoke({"input": state["user_input"]})
    intent = result.content.strip().upper()

    # 兜底
    valid_intents = {"KB_QA", "DATA_QUERY", "CHITCHAT", "HANDOFF", "CLARIFY"}
    if intent not in valid_intents:
        intent = "KB_QA"

    return {
        "intent": intent,
        "processing_steps": [f"意图识别: {intent}"],
    }
