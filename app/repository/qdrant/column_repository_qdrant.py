from app.models.qdrant.column_info_qdrant import ColumnInfoQdrant
from app.repository.qdrant.base_repository_qdrant import BaseQdrantRepository


class ColumnQdrantRepository(BaseQdrantRepository[ColumnInfoQdrant]):
    collection_name = "data_agent_column"
