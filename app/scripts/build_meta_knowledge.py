import argparse
import asyncio
from pathlib import Path

from app.clients.embedding_client import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.core.log import logger
from app.repository.es.value_es_repository import ValueESRepository
from app.repository.mysql.dw_mysql_repository import DWMySQLRepository
from app.repository.mysql.meta_mysql_repository import MetaMySQLRepository
from app.repository.qdrant.column_repository_qdrant import ColumnQdrantRepository
from app.repository.qdrant.metric_repository_qdrant import MetricQdrantRepository
from app.service.meta_knowledge_service import MetaKnowledgeService


async def build(meta_config: Path):
    # 初始化所有client
    dw_mysql_client_manager.init()
    meta_mysql_client_manager.init()
    embedding_client_manager.init()
    qdrant_client_manager.init()
    es_client_manager.init()

    try:
        # 造出所有repository
        async with (
            dw_mysql_client_manager.session_factory() as dw_session,
            meta_mysql_client_manager.session_factory() as meta_session
        ):
            dw_mysql_repository = DWMySQLRepository(dw_session)
            meta_mysql_repository = MetaMySQLRepository(meta_session)

            embedding_client = embedding_client_manager.client

            qdrant_client = qdrant_client_manager.client
            column_repository_qdrant = ColumnQdrantRepository(qdrant_client)
            metric_repository_qdrant = MetricQdrantRepository(qdrant_client)

            es_client = es_client_manager.client
            value_es_repository = ValueESRepository(es_client)

            # 拼出service
            meta_knowledge_service = MetaKnowledgeService(
                dw_mysql_repository=dw_mysql_repository,
                meta_mysql_repository=meta_mysql_repository,
                embedding_client=embedding_client,
                column_repository_qdrant=column_repository_qdrant,
                metric_repository_qdrant=metric_repository_qdrant,
                value_es_repository=value_es_repository
            )

            # 调用service干活
            await meta_knowledge_service.build_meta_knowledge(meta_config)
    except Exception:
        # 全量重建:中途失败只会留下"不完整"的数据,不会积累脏数据,修复后重跑即可
        logger.exception("离线知识库构建失败,请根据上方错误修复后重新执行本命令(可安全重跑)")
        raise
    finally:
        # 关闭所有client
        await dw_mysql_client_manager.close()
        await meta_mysql_client_manager.close()
        await qdrant_client_manager.close()
        await es_client_manager.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True)
    args = parser.parse_args()

    asyncio.run(build(Path(args.config)))
