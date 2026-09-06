import pathlib

from app.clients.embedding_client import EmbeddingClientManager
from app.repository.es.value_es_repository import ValueESRepository
from app.repository.mysql.dw_mysql_repository import DWMySQLRepository
from app.repository.mysql.meta_mysql_repository import MetaMySQLRepository
from app.repository.qdrant.column_repository_qdrant import ColumnQdrantRepository


class MetaKnowledgeService:
    def __init__(self,
                 dw_mysql_repository: DWMySQLRepository,
                 meta_mysql_repository: MetaMySQLRepository,
                 embedding_client: EmbeddingClientManager,
                 column_repository_qdrant: ColumnQdrantRepository,
                 metric_repository_qdrant: MetaMySQLRepository,
                 value_es_repository: ValueESRepository
                 ):
        self.dw_mysql_repository = dw_mysql_repository
        self.meta_mysql_repository = meta_mysql_repository
        self.embedding_client = embedding_client
        self.column_repository_qdrant = column_repository_qdrant
        self.metric_repository_qdrant = metric_repository_qdrant
        self.value_es_repository = value_es_repository

    def build_meta_knowledge(self, path: pathlib):
        # 1. 拿到配置文件的路径,把 yaml 内容读成一个 Python 能用的对象。

        pass