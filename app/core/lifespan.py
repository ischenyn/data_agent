from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.clients.embedding_client import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动阶段
    dw_mysql_client_manager.init()
    meta_mysql_client_manager.init()
    es_client_manager.init()
    qdrant_client_manager.init()
    embedding_client_manager.init()
    yield
    # 关闭阶段
    await dw_mysql_client_manager.close()
    await meta_mysql_client_manager.close()
    await es_client_manager.close()
    await qdrant_client_manager.close()