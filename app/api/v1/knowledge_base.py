"""API 路由 — 知识库管理"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseList,
)
from app.core.kb_service import KBService
from app.dependencies import get_kb_service, get_db

router = APIRouter(prefix="/knowledge-bases", tags=["知识库"])


@router.get("", response_model=KnowledgeBaseList)
async def list_knowledge_bases(
    kb_service: KBService = Depends(get_kb_service),
):
    """获取知识库列表"""
    kbs = await kb_service.list_kbs()
    return KnowledgeBaseList(
        items=[KnowledgeBaseResponse.model_validate(kb) for kb in kbs],
        total=len(kbs),
    )


@router.post("", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    kb_service: KBService = Depends(get_kb_service),
):
    """创建知识库"""
    kb = await kb_service.create_kb(name=data.name, description=data.description)
    return KnowledgeBaseResponse.model_validate(kb)


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    kb_service: KBService = Depends(get_kb_service),
):
    """获取知识库详情"""
    kb = await kb_service.get_kb(kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    return KnowledgeBaseResponse.model_validate(kb)


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    data: KnowledgeBaseUpdate,
    kb_service: KBService = Depends(get_kb_service),
):
    """更新知识库"""
    update_data = data.model_dump(exclude_unset=True)
    kb = await kb_service.update_kb(kb_id, update_data)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    return KnowledgeBaseResponse.model_validate(kb)


@router.delete("/{kb_id}", status_code=204)
async def delete_knowledge_base(
    kb_id: str,
    kb_service: KBService = Depends(get_kb_service),
):
    """删除知识库"""
    deleted = await kb_service.delete_kb(kb_id)
    if not deleted:
        raise HTTPException(404, "知识库不存在")
