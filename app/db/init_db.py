"""数据库初始化 — 创建所有表 + 种子数据"""

import logging
from sqlalchemy import select

from app.db.session import engine, async_session_factory
from app.models.base import Base
import app.models  # noqa: F401 — 一次性导入所有模型
from app.models.prompt import PromptItem

logger = logging.getLogger(__name__)

# 默认提示词（首次启动时写入数据库）
_DEFAULT_PROMPTS = [
    # 运营收益
    {"category": "revenue", "text": "本月营收有多少", "intent": "DATA_QUERY", "sort_order": 0},
    {"category": "revenue", "text": "今年累计营收是多少", "intent": "DATA_QUERY", "sort_order": 1},
    {"category": "revenue", "text": "上周营收对比", "intent": "DATA_QUERY", "sort_order": 2},
    {"category": "revenue", "text": "近14天营收趋势", "intent": "DATA_QUERY", "sort_order": 3},
    {"category": "revenue", "text": "月收入统计总数", "intent": "DATA_QUERY", "sort_order": 4},
    {"category": "revenue", "text": "日收入明细", "intent": "DATA_QUERY", "sort_order": 5},
    {"category": "revenue", "text": "月收入明细列表", "intent": "DATA_QUERY", "sort_order": 6},
    {"category": "revenue", "text": "安心充总收益和成本", "intent": "DATA_QUERY", "sort_order": 7},
    {"category": "revenue", "text": "未开通安心充预计收益", "intent": "DATA_QUERY", "sort_order": 8},
    {"category": "revenue", "text": "安心充每日收益查询", "intent": "DATA_QUERY", "sort_order": 9},
    # 用户订单
    {"category": "orders", "text": "今日订单数量", "intent": "DATA_QUERY", "sort_order": 0},
    {"category": "orders", "text": "本月订单有多少", "intent": "DATA_QUERY", "sort_order": 1},
    {"category": "orders", "text": "近14天订单趋势", "intent": "DATA_QUERY", "sort_order": 2},
    {"category": "orders", "text": "今日新增用户", "intent": "DATA_QUERY", "sort_order": 3},
    {"category": "orders", "text": "本月用户增长", "intent": "DATA_QUERY", "sort_order": 4},
    {"category": "orders", "text": "近14天用户增长趋势", "intent": "DATA_QUERY", "sort_order": 5},
    {"category": "orders", "text": "营收排名第几名", "intent": "DATA_QUERY", "sort_order": 6},
    {"category": "orders", "text": "总交易金额是多少", "intent": "DATA_QUERY", "sort_order": 7},
    # 设备相关
    {"category": "device", "text": "充电桩设备状态", "intent": "DATA_QUERY", "sort_order": 0},
    {"category": "device", "text": "充电枪使用状态", "intent": "DATA_QUERY", "sort_order": 1},
    {"category": "device", "text": "充电桩在线率", "intent": "DATA_QUERY", "sort_order": 2},
    {"category": "device", "text": "近14天充电量趋势", "intent": "DATA_QUERY", "sort_order": 3},
    {"category": "device", "text": "今日充电量统计", "intent": "DATA_QUERY", "sort_order": 4},
    {"category": "device", "text": "本月充电量统计", "intent": "DATA_QUERY", "sort_order": 5},
    {"category": "device", "text": "XK-630充电主机功能介绍", "intent": "KB_QA", "sort_order": 6},
    {"category": "device", "text": "XK-63x充电终端说明书", "intent": "KB_QA", "sort_order": 7},
    {"category": "device", "text": "Z2直流桩用户手册内容", "intent": "KB_QA", "sort_order": 8},
    {"category": "device", "text": "智能车位锁怎么使用", "intent": "KB_QA", "sort_order": 9},
    {"category": "device", "text": "交流控制器安装说明", "intent": "KB_QA", "sort_order": 10},
    {"category": "device", "text": "景观式取电立柱规格", "intent": "KB_QA", "sort_order": 11},
    {"category": "device", "text": "充电桩的保修政策是什么", "intent": "KB_QA", "sort_order": 12},
]


async def init_database():
    """创建所有未存在的表 + 写入默认提示词"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建/验证完成")

    # 写入默认提示词（仅首次）
    async with async_session_factory() as db:
        result = await db.execute(select(PromptItem).limit(1))
        if not result.scalar_one_or_none():
            for data in _DEFAULT_PROMPTS:
                db.add(PromptItem(**data))
            await db.commit()
            logger.info("默认提示词已写入 (%d 条)", len(_DEFAULT_PROMPTS))
