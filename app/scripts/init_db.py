"""
初始化 meta 库表结构(幂等,可重复执行)。

用法:
    python -m app.scripts.init_db

说明:
    - 连接 conf/app_config.yaml 中的 db_meta,使用 SQLAlchemy 自动建表。
    - 表已存在则跳过,不会破坏已有数据。
    - 前提: meta 数据库本身必须已存在(例如 docker compose 启动 MySQL 时
      已通过 docker/mysql/meta.sql 自动创建)。
"""
import asyncio

from sqlalchemy.exc import OperationalError

from app.clients.mysql_client_manager import meta_mysql_client_manager
from app.models.mysql import (  # noqa: F401  确保模型注册到 Base.metadata
    column_info_mysql,
    column_metric_mysql,
    metric_info_mysql,
    table_info_mysql,
)
from app.models.mysql.base import Base


async def init_db():
    meta_mysql_client_manager.init()
    try:
        async with meta_mysql_client_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("meta 库表结构初始化完成")
    except OperationalError as e:
        raise RuntimeError(
            "无法连接 meta 数据库。请确认 MySQL 已启动、conf/app_config.yaml 的 db_meta "
            "配置正确,且 meta 数据库已创建(可通过 docker compose 启动 MySQL 自动初始化)。"
        ) from e
    finally:
        await meta_mysql_client_manager.close()


if __name__ == '__main__':
    asyncio.run(init_db())
