from app.clients.embedding_client import embedding_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.models.qdrant.metric_info_qdrant import MetricInfoQdrant
from app.repository.qdrant.base_repository_qdrant import BaseQdrantRepository


class MetricQdrantRepository(BaseQdrantRepository[MetricInfoQdrant]):
    collection_name = "data_agent_metric"


if __name__ == '__main__':
    import asyncio

    async def test():
        embedding_client_manager.init()
        embedding_client = embedding_client_manager.client

        qdrant_client_manager.init()
        repo = MetricQdrantRepository(qdrant_client_manager.client)

        await repo.ensure_collection()

        vec1 = await embedding_client.aembed_query("GMV")
        vec2 = await embedding_client.aembed_query("客单价")
        await repo.upsert(
            ids=[1, 2],
            embeddings=[vec1, vec2],
            payloads=[
                {"id": "GMV", "name": "GMV", "description": "成交总额"},
                {"id": "AOV", "name": "AOV", "description": "客单价"},
            ],
        )

        query_vec = embedding_client.embed_query("统计一下GMV")
        result = await repo.search(query_vec, score_threshold=0.5, limit=5)
        print(result)

        await qdrant_client_manager.close()

    asyncio.run(test())
