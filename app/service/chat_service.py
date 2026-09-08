from langgraph.graph.state import CompiledStateGraph

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.clients.embedding_client import LocalEmbeddingClient
from app.repository.es.value_es_repository import ValueESRepository
from app.repository.mysql.dw_mysql_repository import DWMySQLRepository
from app.repository.mysql.meta_mysql_repository import MetaMySQLRepository
from app.repository.qdrant.column_repository_qdrant import ColumnQdrantRepository
from app.repository.qdrant.metric_repository_qdrant import MetricQdrantRepository


class ChatService:
    def __init__(self,
                 graph: CompiledStateGraph,
                 embedding_client: LocalEmbeddingClient,
                 meta_mysql_repository: MetaMySQLRepository,
                 dw_mysql_repository: DWMySQLRepository,
                 column_qdrant_repository: ColumnQdrantRepository,
                 value_es_repository: ValueESRepository,
                 metric_qdrant_repository: MetricQdrantRepository,
                 ):
        self.graph = graph
        self.embedding_client = embedding_client
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.value_es_repository = value_es_repository
        self.metric_qdrant_repository = metric_qdrant_repository

    async def stream_chat(self, query: str):
        # 第1步：用这次的 query，造一个新的 DataAgentState
        state = DataAgentState(query=query)
        # 第2步：用 self 身上存好的6个工具，拼一个 context 字典
        #        （对照 DataAgentContext 里的6个key名字）
        context = DataAgentContext(
            embedding_client=self.embedding_client,
            meta_mysql_repository=self.meta_mysql_repository,
            dw_mysql_repository=self.dw_mysql_repository,
            column_repository_qdrant=self.column_qdrant_repository,
            metric_repository_qdrant=self.metric_qdrant_repository,
            value_es_repository=self.value_es_repository,
        )
        # 第3步：调用
        #        用 async for 循环，把每个 chunk 依次 yield 出去
        chunks = self.graph.astream(input=state, context=context, stream_mode="custom")
        async for chunk in chunks:
            yield chunk
