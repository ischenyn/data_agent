from pathlib import Path

from app.clients.mysql_client_manager import meta_mysql_client_manager
from app.repository.mysql.meta_mysql_repository import MetaMySQLRepository
from app.service.meta_knowledge_service import MetaKnowledgeService


async def build(config_path: Path):
    meta_mysql_client_manager.init()
    async with meta_mysql_client_manager.session_factory() as session:
        meta_mysql_repository = MetaMySQLRepository(session)
        meta_knowledge_service = MetaKnowledgeService(meta_mysql_repository)
        await meta_knowledge_service.build(config_path)


