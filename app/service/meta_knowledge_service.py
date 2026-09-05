from pathlib import Path

from app.conf.config_loader import load_config
from app.conf.meta_config import MetaConfig
from app.repository.mysql.meta_mysql_repository import MetaMySQLRepository


class MetaKnowledgeService:
    def __init__(self, meta_mysql_repository: MetaMySQLRepository):
        self.meta_mysql_repository = meta_mysql_repository


    async def build(self, config_path: Path):
        # 1.加载配置文件
        meta_config: MetaConfig = load_config(config_path, MetaConfig)
        # 2.处理表信息
        if meta_config.tables:
            pass




        # 3.处理指标信息
        if meta_config.metrics:
            pass


