"""LangGraph 对话工作流图定义 — 编译后的可执行图"""

import logging

from langgraph.graph import StateGraph, END

from app.workflows.state import ChatState
from app.workflows.nodes.router_node import router_node
from app.workflows.nodes.retrieval_node import retrieval_node
from app.workflows.nodes.generation_node import generation_node
from app.workflows.nodes.data_query_node import data_query_node
from app.workflows.nodes.guardrails_node import guardrails_node
from app.workflows.nodes.memory_node import memory_node

logger = logging.getLogger(__name__)


def build_chat_graph() -> StateGraph:
    """构建并编译对话工作流图

    节点流程:
        router → (KB_QA → retrieval,
                  DATA_QUERY → data_query,
                  CHITCHAT/HANDOFF → generation)
               → generation → guardrails → memory → END

    Returns:
        编译后的 StateGraph (Runnable)
    """
    workflow = StateGraph(ChatState)

    # ── 注册节点 ──
    workflow.add_node("router", router_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("data_query", data_query_node)
    workflow.add_node("generation", generation_node)
    workflow.add_node("guardrails", guardrails_node)
    workflow.add_node("memory", memory_node)

    # ── 入口 ──
    workflow.set_entry_point("router")

    # ── 条件边：根据意图路由 ──
    workflow.add_conditional_edges(
        "router",
        lambda state: state.get("intent", "KB_QA"),
        {
            "KB_QA": "retrieval",
            "DATA_QUERY": "data_query",
            "CHITCHAT": "generation",
            "HANDOFF": "generation",
            "CLARIFY": "generation",       # 追问走 generation，基于对话历史回答
        },
    )

    # ── 固定边 ──
    workflow.add_edge("retrieval", "generation")
    workflow.add_edge("data_query", "generation")
    workflow.add_edge("generation", "guardrails")
    workflow.add_edge("guardrails", "memory")
    workflow.add_edge("memory", END)

    return workflow.compile()
