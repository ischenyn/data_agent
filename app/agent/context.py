from typing import TypedDict

from app.clients.embedding_client import LocalEmbeddingClient
from app.repository.es.value_es_repository import ValueESRepository
from app.repository.mysql.dw_mysql_repository import DWMySQLRepository
from app.repository.mysql.meta_mysql_repository import MetaMySQLRepository
from app.repository.qdrant.column_repository_qdrant import ColumnQdrantRepository
from app.repository.qdrant.metric_repository_qdrant import MetricQdrantRepository


class DataAgentContext(TypedDict):
    dw_mysql_repository: DWMySQLRepository  # 数据仓库MySQL库
    meta_mysql_repository: MetaMySQLRepository  # 元数据MySQL库
    column_repository_qdrant: ColumnQdrantRepository  # 字段向量库
    metric_repository_qdrant: MetricQdrantRepository  # 指标向量库
    value_es_repository: ValueESRepository  # 字段值全文检索库
    embedding_client: LocalEmbeddingClient  # 向量服务客户端
