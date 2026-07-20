"""LangGraph 节点 — 数据查询

当用户询问营收、订单、电量等数据时，调用外部 API 获取数据并生成回答。
"""

import json
import logging
import time
from datetime import date, timedelta
from typing import Optional

from httpx import AsyncClient, Timeout

from app.config import settings
from app.llm.factory import LLMFactory
from app.workflows.state import ChatState

logger = logging.getLogger(__name__)

# 外部 API 基础地址（从 config/settings 读取）
BASE_URL = settings.EXTERNAL_API_BASE_URL

# API 端点描述，供 LLM 选择（日期由 _build_body 动态计算）
API_ENDPOINTS = [
    {"path": "/home/statRevenue", "desc": "统计营收数据（今日/本月/今年营收）", "method": "POST", "body": {}},
    {"path": "/home/statOrders", "desc": "统计订单数量（今日/昨日/今年/近14天趋势）", "method": "POST", "body": {}},
    {"path": "/home/statUsers", "desc": "统计用户数量（今日/昨日/今年/近14天趋势）", "method": "POST", "body": {}},
    {"path": "/home/statKwh", "desc": "统计电量（今日/今年/近14天趋势）", "method": "POST", "body": {}},
    {"path": "/home/statDevStates", "desc": "统计设备和枪的状态数量", "method": "POST", "body": {}},
    {"path": "/stat/statOrdersDays", "desc": "近14天(type=1)或近12月(type=2)订单数量趋势（仅支持最近时段）", "method": "POST", "body": {"type": 1}},
    {"path": "/stat/statKwhsDays", "desc": "近14天(type=1)或近12月(type=2)电量趋势（仅支持最近时段）", "method": "POST", "body": {"type": 1}},
    {"path": "/stat/statUsersDays", "desc": "近14天(type=1)或近12月(type=2)用户数量趋势（仅支持最近时段）", "method": "POST", "body": {"type": 1}},
    {"path": "/home/statRevenueDays", "desc": "近14天(type=1)或近12月(type=2)营收趋势（每日明细，仅支持最近时段）", "method": "POST", "body": {"type": 1}},
    {"path": "/stat/statRevenueMonthTotal", "desc": "月收入汇总（总收入/订单/电量等）", "method": "POST", "body": {}},
    {"path": "/stat/statRevenueMonthList", "desc": "月收入明细（按月拆分的逐月收入列表）", "method": "POST", "body": {}},
    {"path": "/stat/statRevenueDayTotal", "desc": "日收入汇总（单日或自定义日期范围的总收入/订单/电量等）", "method": "POST", "body": {}},
    {"path": "/stat/statRevenueDayList", "desc": "日收入明细（按日拆分的每天收入列表详情）", "method": "POST", "body": {}},
]

# ── LLM 日期解析 ───────────────────────────────────────────────────
async def _parse_date_range(user_input: str) -> dict:
    """用 LLM 从用户问题中提取日期范围

    Returns:
        {"dateBegin": "2026-07-01", "dateEnd": "2026-07-06"} 或 {}
    """
    today = date.today()
    prompt = f"""你是一个日期解析助手。从用户问题中提取查询的日期范围，返回 JSON。
今天日期: {today.isoformat()}

规则:
- 只有用户指定了明确的起止日期（如"6月8号到12号"、"6月1日至6月6日"），才返回 {{"dateBegin": "...", "dateEnd": "..."}}
- 如果用户说的是**相对时间段**（如"近14天"、"本月"、"今年"、"上周"），**返回 {{}}**（空对象）
- 如果用户只说了"昨天"，返回 {{}}
- "近14天"、"近7天"、"近30天" → 一律返回 {{}}
- 日期格式: YYYY-MM-DD

示例:
"7月1号到6号的营收" → {{"dateBegin": "{today.year}-07-01", "dateEnd": "{today.year}-07-06"}}
"近14天营收趋势" → {{}}
"近7天订单" → {{}}
"本月营收" → {{}}
"营收情况" → {{}}
"昨天营收" → {{}}
"今年营收" → {{}}

用户问题: {user_input}
只返回 JSON，不要其他文字。"""

    llm = LLMFactory.get_fast_model(temperature=0.0)
    try:
        result = await llm.ainvoke(prompt)
        parsed = json.loads(result.content.strip())
        if isinstance(parsed, dict) and "dateBegin" in parsed and "dateEnd" in parsed:
            return parsed
    except Exception as e:
        logger.debug("日期解析失败: %s", e)
    return {}


# ── 日期计算 ───────────────────────────────────────────────────────
def _build_body(endpoint: dict, user_input: str = "", parsed_dates: dict = None) -> dict:
    """根据端点和用户问题动态计算请求参数"""
    body = endpoint.get("body", {}).copy()
    path = endpoint["path"]
    today = date.today()

    # 如果 LLM 解析出了日期：日收入汇总/月收入汇总接受 dateBegin/dateEnd
    if parsed_dates and "dateBegin" in parsed_dates and "dateEnd" in parsed_dates:
        if path in ("/stat/statRevenueDayTotal", "/stat/statRevenueMonthTotal"):
            body["dateBegin"] = parsed_dates["dateBegin"]
            body["dateEnd"] = parsed_dates["dateEnd"]
            return body

    # 无解析日期时的默认值
    if path in ("/stat/statRevenueDayTotal", "/stat/statRevenueDayList"):
        body["dateBegin"] = today.isoformat()
        body["dateEnd"] = today.isoformat()
    elif path in ("/stat/statRevenueMonthTotal", "/stat/statRevenueMonthList"):
        body["dateBegin"] = today.replace(day=1).isoformat()
        body["dateEnd"] = today.isoformat()

    return body


# ── 日期兜底路由 ───────────────────────────────────────────────────
async def _resolve_endpoint(api_choice: dict, user_input: str) -> dict:
    """如果用户指定了日期范围，自动切到支持 dateBegin/dateEnd 的接口"""
    if not user_input:
        return api_choice

    parsed = await _parse_date_range(user_input)
    if not parsed or "dateBegin" not in parsed:
        return api_choice  # 没指定日期，走原接口

    # 选了营收趋势但用户指定了日期 → 切到 statRevenueDayTotal（支持自定义日期）
    if api_choice["path"] == "/home/statRevenueDays":
        logger.info("日期兜底: %s → /stat/statRevenueDayTotal (dates=%s)",
                     api_choice["path"], parsed)
        return {"path": "/stat/statRevenueDayTotal",
                "desc": "日收入汇总（支持自定义日期范围）",
                "method": "POST", "body": parsed}

    # 选了用户/订单/电量趋势但用户指定了日期 → 这些接口不支持自定义日期，返回 None
    if api_choice["path"] in ("/stat/statUsersDays", "/stat/statOrdersDays", "/stat/statKwhsDays"):
        logger.info("趋势接口 %s 不支持自定义日期，退回", api_choice["path"])
        return None

    return api_choice


async def data_query_direct(user_input: str, user_token: str | None = None, chat_history: str = "") -> Optional[dict]:
    """直通数据查询：不依赖 LangGraph 状态，直接返回结果

    Args:
        user_input: 用户问题
        user_token: 用户的 Bearer Token（用于调外部 API）
        chat_history: 历史对话上下文（用于模糊查询时参考前文）

    Returns:
        dict with answer, chart_config, sources 或 None（非数据查询）
    """
    api_choice = await _select_api(user_input, chat_history)
    if not api_choice:
        return None
    api_choice = await _resolve_endpoint(api_choice, user_input)
    try:
        api_data = await _call_api(api_choice, token=user_token, user_input=user_input)
    except Exception as e:
        logger.error("API 调用失败（直通路径）", exc_info=True)
        return None
    answer, chart_config = await _generate_answer(user_input, api_choice["path"], api_data, chat_history)
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
    # 日期兜底：如果用户指定了日期范围，切到支持 dateBegin/dateEnd 的接口
    api_choice = await _resolve_endpoint(api_choice, user_input)
    select_elapsed = round((time.time() - t0) * 1000)
    if not api_choice:
        return {
            "answer": '抱歉，我不太确定您想查询什么数据，请更具体地描述，例如："营收情况"、"订单数量"、"电量统计"、"设备状态"等。',
            "processing_steps": [f"数据查询: 未匹配到合适API({select_elapsed}ms)"],
        }

    # 2. 用用户的 token 调用 API
    t0 = time.time()
    try:
        api_data = await _call_api(api_choice, token=user_token, user_input=user_input)
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
    prompt = f"""判断用户的问题是否需要查询新的数据，从以下 API 中选择最匹配的一个。
- 如果用户的问题是**模糊的后续追问**（如"给出方案"、"然后呢"、"为什么"、"怎么办"、"分析一下"等），说明不需要查新数据，返回 0
- 如果用户明确问了某项数据（如营收、订单、电量等），返回对应的序号

可选 API：
{numbered_list}
{history_part}
用户问题: {user_input}
只返回序号（数字 0-{len(API_ENDPOINTS)}），不要其他文字。"""

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


async def _call_api(endpoint: dict, token: str | None = None, user_input: str = "") -> dict:
    """调用外部 API（日期参数自动解析用户语义）

    Args:
        endpoint: API 端点配置
        token: 用户的 Bearer Token
        user_input: 用户问题原文（自动提取日期范围）
    """
    if not token:
        raise ValueError("缺少 API 访问凭证 (token)")

    # LLM 解析日期（如"7月1号到6号" → dateBegin/dateEnd）
    parsed_dates = await _parse_date_range(user_input) if user_input else {}

    url = f"{BASE_URL}{endpoint['path']}"
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    }
    body = _build_body(endpoint, user_input, parsed_dates)

    logger.info("API 请求: %s body=%s", endpoint['path'], body)

    async with AsyncClient(timeout=Timeout(settings.EXTERNAL_API_TIMEOUT)) as client:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def _generate_answer(user_input: str, api_path: str, api_data: dict, chat_history: str = "") -> tuple:
    """用 LLM 根据 API 返回的数据生成自然语言回答 + 图表配置"""
    data_str = json.dumps(api_data, ensure_ascii=False, indent=2)
    data = api_data.get("data") or {}

    # 自动生成图表配置（仅趋势类接口生成图表）
    chart_config = None
    list_data = None
    _trend_paths = ("/home/statRevenueDays", "/stat/statOrdersDays",
                    "/stat/statKwhsDays", "/stat/statUsersDays")
    if any(p in api_path for p in _trend_paths):
        if isinstance(data, dict):
            list_data = data.get("list") or data.get("list14") or data.get("rows")
        elif isinstance(data, list):
            list_data = data

    # 只有超过 5 天的趋势数据才生成图表
    if list_data and isinstance(list_data, list) and len(list_data) > 5:
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

请用自然、简短的语言回答用户，突出关键数据。如果数据包含金额，带上单位（元）。如果数据包含趋势，简要说明趋势方向。
**重要规则：**
1. 不要输出代码中的字段名（如 todayNum、list14、resValue、resKey 等）
2. **绝对不要提及任何 API 路径、接口名、系统内部的端点名称**
3. 如果数据的时间范围与用户请求的不一致，直接告诉用户当前可提供的是哪个时间范围的数据"""

    llm = LLMFactory.get_fast_model(temperature=0.3, streaming=False)
    result = await llm.ainvoke(prompt)
    return result.content, chart_config
