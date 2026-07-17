"""API 路由 — 提示词管理"""

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.dependencies import get_db
from app.models.prompt import PromptItem

router = APIRouter(prefix="/prompts", tags=["提示词"])


@router.get("")
async def get_prompts(db=Depends(get_db)):
    """获取所有启用的提示词（按分类分组）"""
    result = await db.execute(
        select(PromptItem)
        .where(PromptItem.is_active == True)
        .order_by(PromptItem.category, PromptItem.sort_order)
    )
    items = result.scalars().all()

    # 按分类分组
    tabs = {"全部": None}
    prompts = {}
    for item in items:
        if item.category not in prompts:
            prompts[item.category] = []
        prompts[item.category].append({
            "text": item.text,
            "intent": item.intent,
        })

    # 构建分类标签列表
    category_labels = {
        "revenue": "运营收益",
        "orders": "用户订单",
        "device": "设备相关",
    }

    tab_list = [{"key": "all", "label": "全部"}]
    for cat in prompts:
        tab_list.append({
            "key": cat,
            "label": category_labels.get(cat, cat),
        })

    return {
        "tabs": tab_list,
        "prompts": prompts,
    }
