"""Qdrant Collection 管理 — 多集合、别名、备份"""

from app.qdrant.client import QdrantClientWrapper


class CollectionManager:
    """管理知识库与 Qdrant collection 的映射"""

    def __init__(self, qdrant: QdrantClientWrapper):
        self.qdrant = qdrant

    async def create_kb_collection(self, kb_id: str) -> bool:
        """为知识库创建专属集合"""
        collection_name = f"kb_{kb_id}"
        # 使用 client 的原始方法创建
        self.qdrant.client.create_collection(
            collection_name=collection_name,
            vectors_config=self.qdrant.client.get_collection(
                "knowledge_base"
            ).config.params.vectors,
        )
        return True

    async def delete_kb_collection(self, kb_id: str):
        """删除知识库对应集合"""
        self.qdrant.client.delete_collection(f"kb_{kb_id}")
