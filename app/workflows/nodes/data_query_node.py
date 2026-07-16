"""LangGraph 节点 — 数据查询

当用户询问营收、订单、电量等数据时，调用外部 API 获取数据并生成回答。
"""

import json
import logging
import time
from typing import Optional

from httpx import AsyncClient, Timeout

from app.config import settings
from app.llm.factory import LLMFactory
from app.workflows.state import ChatState

logger = logging.getLogger(__name__)

# 外部 API 基础地址（从 config/settings 读取）
BASE_URL = settings.EXTERNAL_API_BASE_URL

# API 端点描述，供 LLM 选择
API_ENDPOINTS = [
    {"path": "/home/statRevenue", "desc": "统计营收数据（今日/本月/今年营收）", "method": "POST", "body": {}},
    {"path": "/home/statOrders", "desc": "统计订单数量（今日/昨日/今年/近14天趋势）", "method": "POST", "body": {}},
    {"path": "/home/statUsers", "desc": "统计用户数量（今日/昨日/今年/近14天趋势）", "method": "POST", "body": {}},
    {"path": "/home/statKwh", "desc": "统计电量（今日/今年/近14天趋势）", "method": "POST", "body": {}},
    {"path": "/home/statDevStates", "desc": "统计设备和枪的状态数量", "method": "POST", "body": {}},
    {"path": "/stat/statOrdersDays", "desc": "近14天(type=1)或近12月(type=2)订单数量趋势", "method": "POST", "body": {"type": 1}},
    {"path": "/stat/statKwhsDays", "desc": "近14天(type=1)或近12月(type=2)电量趋势", "method": "POST", "body": {"type": 1}},
    {"path": "/stat/statUsersDays", "desc": "近14天(type=1)或近12月(type=2)用户数量趋势", "method": "POST", "body": {"type": 1}},
    {"path": "/home/statRevenueDays", "desc": "近14天(type=1)或近12月(type=2)营收趋势（每日明细）", "method": "POST", "body": {"type": 1}},
    {"path": "/stat/statRevenueMonthTotal", "desc": "月收入统计总数（总收入/订单/电量等）", "method": "POST", "body": {"dateBegin": "2026-01-01", "dateEnd": "2026-07-31"}},
    {"path": "/stat/statRevenueDayTotal", "desc": "日收入统计总数（总收入/订单/电量等）", "method": "POST", "body": {"dateBegin": "2026-07-01", "dateEnd": "2026-07-14"}},
]


async def data_query_direct(user_input: str, user_token: str | None = None) -> Optional[dict]:
    """直通数据查询：不依赖 LangGraph 状态，直接返回结果

    Args:
        user_input: 用户问题
        user_token: 用户的 Bearer Token（用于调外部 API）

    Returns:
        dict with answer, chart_config, sources 或 None（非数据查询）
    """
    api_choice = await _select_api(user_input)
    if not api_choice:
        return None
    try:
        api_data = await _call_api(api_choice, token=user_token)
    except Exception as e:
        logger.error("API 调用失败（直通路径）", exc_info=True)
        return None
    answer, chart_config = await _generate_answer(user_input, api_choice["path"], api_data, "")
    return {
        "answer": answer,
        "chart_config": chart_config,
        "sources": [{"doc_name": "API: " + api_choice["path"], "text": str(api_data)[:200]}],
    }


async def data_query_node(state: ChatState) -> dict:
    """数据查询节点：意图识别 -> 选 API -> 调用 -> 生成回答"""
    start = time.time()
    user_input = state["user_input"]
    user_token = state.get("user_token")

    if not user_token:
        return {
            "answer": "无法查询数据：缺少访问凭证，请重新登录后重试。",
            "processing_steps": ["数据查询: 缺少 token"],
        }

    # 提取历史记录，支持"那上个月呢"这类追问
    from app.utils.common import format_chat_history
    chat_history = format_chat_history(state.get("messages", []))

    # 1. 用 LLM 选择调哪个 API（带上历史上下文）
    t0 = time.time()
    api_choice = await _select_api(user_input, chat_history)
    select_elapsed = round((time.time() - t0) * 1000)
    if not api_choice:
        return {
            "answer": '抱歉，我不太确定您想查询什么数据，请更具体地描述，例如："营收情况"、"订单数量"、"电量统计"、"设备状态"等。',
            "processing_steps": [f"数据查询: 未匹配到合适API({select_elapsed}ms)"],
        }

    # 2. 用用户的 token 调用 API
    t0 = time.time()
    try:
        api_data = await _call_api(api_choice, token=user_token)
    except Exception as e:
        logger.error("API 调用失败（工作流路径）", exc_info=True)
        return {
            "answer": "查询数据时遇到问题，请稍后再试。",
            "processing_steps": [f"数据查询失败({select_elapsed}ms)"],
        }
    api_elapsed = round((time.time() - t0) * 1000)

    # 3. 用 LLM 生成回答 + 图表配置（带上历史上下文）
    t0 = time.time()
    answer, chart_config = await _generate_answer(user_input, api_choice["path"], api_data, chat_history)
    gen_elapsed = round((time.time() - t0) * 1000)

    total_elapsed = round((time.time() - start) * 1000)
    logger.info("数据查询: path=%s, select=%dms, api=%dms, gen=%dms, total=%dms",
                api_choice["path"], select_elapsed, api_elapsed, gen_elapsed, total_elapsed)

    return {
        "answer": answer,
        "chart_config": chart_config,
        "processing_steps": [f"数据查询({api_choice['path']}) {total_elapsed}ms"],
        "sources": [{"doc_name": "API: " + api_choice["path"], "text": str(api_data)[:200]}],
    }


async def _select_api(user_input: str, chat_history: str = "") -> Optional[dict]:
    """用 LLM 语义理解用户问题，匹配最合适的 API 端点"""
    # 给每个端点编号，LLM 返回编号实现精确匹配
    numbered_list = "\n".join(
        f"{i+1}. {e['path']}: {e['desc']}"
        for i, e in enumerate(API_ENDPOINTS)
    )

    history_part = f"\n历史对话：\n{chat_history}\n" if chat_history else ""
    prompt = f"""根据用户的问题和历史对话，从以下 API 中选择最匹配的一个。
只返回序号（数字），不要其他文字。

可选 API：
{numbered_list}
{history_part}
用户问题: {user_input}"""

    llm = LLMFactory.get_fast_model(temperature=0.0, streaming=False)
    result = await llm.ainvoke(prompt)
    answer = result.content.strip()

    # 尝试从 LLM 输出中提取数字序号
    import re
    numbers = re.findall(r'\d+', answer)
    if numbers:
        idx = int(numbers[0]) - 1
        if 0 <= idx < len(API_ENDPOINTS):
            return API_ENDPOINTS[idx]

    return None


async def _call_api(endpoint: dict, token: str | None = None) -> dict:
    """调用外部 API

    Args:
        endpoint: API 端点配置
        token: 用户的 Bearer Token（不传则抛异常）
    """
    if not token:
        raise ValueError("缺少 API 访问凭证 (token)")

    url = f"{BASE_URL}{endpoint['path']}"
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    }
    body = endpoint.get("body", {})

    async with AsyncClient(timeout=Timeout(settings.EXTERNAL_API_TIMEOUT)) as client:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def _generate_answer(user_input: str, api_path: str, api_data: dict, chat_history: str = "") -> tuple:
    """用 LLM 根据 API 返回的数据生成自然语言回答 + 图表配置"""
    data_str = json.dumps(api_data, ensure_ascii=False, indent=2)
    data = api_data.get("data") or {}

    # 自动生成图表配置（通用的折线图/指标卡）
    chart_config = None
    list_data = None
    if isinstance(data, dict):
        list_data = data.get("list") or data.get("list14") or data.get("rows")
    elif isinstance(data, list):
        list_data = data

    # 如果有趋势数据（list 包含 resKey/resValue），生成折线图
    if list_data and isinstance(list_data, list) and len(list_data) > 0:
        first = list_data[0]
        if isinstance(first, dict) and ("resKey" in first or "day" in first or "date" in first):
            keys = [d.get("resKey") or d.get("day") or d.get("date", "") for d in list_data]
            vals = [float(d.get("resValue") or d.get("totalRevenue") or d.get("value", 0)) for d in list_data]
            label = "值"
            if "revenue" in api_path.lower() or "money" in api_path.lower():
                label = "营收(元)"
            elif "kwh" in api_path.lower():
                label = "电量(kWh)"
            elif "order" in api_path.lower():
                label = "订单数"
            elif "user" in api_path.lower():
                label = "用户数"
            chart_config = {
                "type": "line",
                "title": label,
                "keys": keys,
                "values": vals,
                "color": "#0f3460",
            }

    # LLM 生成自然语言回答
    history_part = f"\n历史对话：\n{chat_history}\n" if chat_history else ""
    prompt = f"""你是一个数据助手，根据 API 返回的数据回答用户的问题。

调用 API: {api_path}
返回数据:
```json
{data_str}
```
{history_part}
用户问题: {user_input}

请用自然、友好的语言回答用户，突出关键数据。如果数据包含金额，带上单位（元）。如果数据包含趋势，简要说明趋势方向。"""

    llm = LLMFactory.get_fast_model(temperature=0.3, streaming=False)
    result = await llm.ainvoke(prompt)
    return result.content, chart_config
