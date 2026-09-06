from app.clients.embedding_client import embedding_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.models.qdrant.column_info_qdrant import ColumnInfoQdrant
from app.repository.qdrant.base_repository_qdrant import BaseQdrantRepository


class ColumnQdrantRepository(BaseQdrantRepository[ColumnInfoQdrant]):
    collection_name = "data_agent_column"


if __name__ == '__main__':
    import asyncio

    async def test():
        embedding_client_manager.init()
        embedding_client = embedding_client_manager.client

        qdrant_client_manager.init()
        repo = ColumnQdrantRepository(qdrant_client_manager.client)

        await repo.ensure_collection()

        # 造两条假数据先写进去
        vec1 = await embedding_client.aembed_query("地区名称")
        vec2 = await embedding_client.aembed_query("产品分类")
        await repo.upsert(
            ids=[1, 2],
            embeddings=[vec1, vec2],
            payloads=[
                {"id": "test.region", "name": "region_name", "description": "地区名称"},
                {"id": "test.category", "name": "category", "description": "产品分类"},
            ],
        )

        # 用一个相近的词去搜
        query_vec = embedding_client.embed_query("华东大区")
        result = await repo.search(query_vec, score_threshold=0.5, limit=5)
        print(result)

        await qdrant_client_manager.close()

    asyncio.run(test())
