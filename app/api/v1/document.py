"""API 路由 — 文档管理"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pathlib import Path

from app.config import settings
from app.schemas.document import DocumentResponse, DocumentList
from app.core.kb_service import KBService
from app.dependencies import get_kb_service

router = APIRouter(prefix="/knowledge-bases/{kb_id}/documents", tags=["文档"])


@router.get("", response_model=DocumentList)
async def list_documents(
    kb_id: str,
    kb_service: KBService = Depends(get_kb_service),
):
    """获取知识库下的文档列表"""
    docs = await kb_service.list_documents(kb_id)
    return DocumentList(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    kb_service: KBService = Depends(get_kb_service),
):
    """上传文档并自动执行摄入流水线"""
    # 验证知识库存在
    kb = await kb_service.get_kb(kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")

    # 验证文件类型
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型: {ext}")

    # 保存文件
    content = await file.read()
    file_path = await kb_service.save_upload(content, file.filename, kb_id)

    # 执行摄入
    doc = await kb_service.ingest_document(
        kb_id=kb_id,
        file_path=file_path,
        file_type=ext.lstrip("."),
        original_filename=file.filename,
    )

    return DocumentResponse.model_validate(doc)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    kb_id: str,
    doc_id: str,
    kb_service: KBService = Depends(get_kb_service),
):
    """删除文档"""
    deleted = await kb_service.delete_document(doc_id)
    if not deleted:
        raise HTTPException(404, "文档不存在")
