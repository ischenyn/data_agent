import asyncio
from typing import Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from app.config.app_config import QdrantConfig, app_config


class QdrantClientManager:
    def __init__(self, qdrant_config: QdrantConfig):
        self.qdrant_config = qdrant_config
        self.client: Optional[AsyncQdrantClient] = None

    def _get_url(self):
        return f"http://{self.qdrant_config.host}:{self.qdrant_config.port}"

    def init(self):
        self.client = AsyncQdrantClient(url=self._get_url())

    async def close(self):
        if self.client:
            await self.client.close()

qdrant_client_manager = QdrantClientManager(app_config.qdrant)

if __name__ == '__main__':
    qdrant_client_manager.init()

    async def test():
        client = qdrant_client_manager.client
        if not await client.collection_exists("test_collection"):
            await client.create_collection(
                collection_name="test_collection",
                vectors_config=VectorParams(size=4, distance=Distance.DOT),
            )

        operation_info = await client.upsert(
            collection_name="test_collection",
            wait=True,
            points=[
                PointStruct(id=1, vector=[0.05, 0.61, 0.76, 0.74], payload={"city": "Berlin"}),
                PointStruct(id=2, vector=[0.19, 0.81, 0.75, 0.11], payload={"city": "London"}),
                PointStruct(id=3, vector=[0.36, 0.55, 0.47, 0.94], payload={"city": "Moscow"}),
                PointStruct(id=4, vector=[0.18, 0.01, 0.85, 0.80], payload={"city": "New York"}),
                PointStruct(id=5, vector=[0.24, 0.18, 0.22, 0.44], payload={"city": "Beijing"}),
                PointStruct(id=6, vector=[0.35, 0.08, 0.11, 0.44], payload={"city": "Mumbai"}),
            ],
        )
        print(operation_info)

        # result = await client.query_points(
        #     collection_name="test_collection",
        #     query=[0.2, 0.1, 0.9, 0.7],
        #     with_payload=False,
        #     limit=3
        # )

        result = await client.query_points(
            collection_name="test_collection",
            query=[0.2, 0.1, 0.9, 0.7],
            query_filter=Filter(
                must=[FieldCondition(key="city", match=MatchValue(value="London"))]
            ),
            with_payload=True,
            limit=3,
        )

        search_result = result.points

        print(search_result)

    asyncio.run(test())
