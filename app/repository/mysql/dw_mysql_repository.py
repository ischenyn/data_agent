from typing import Any
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.clients.mysql_client_manager import dw_mysql_client_manager


class DWMySQLRepository:
    def __init__(self, dw_session: AsyncSession):
        self.dw_session = dw_session

    async def get_column_types(self, table_name: str) -> dict[str, str]:
        """
        获取表中各字段类型
        :param table_name:表名称
        :return: 各字段类型字典
        """
        sql = text(f"show columns from {table_name}")
        result = await self.dw_session.execute(sql)
        return {row.Field: row.Type for row in result.fetchall()}

    async def get_column_values(self, table_name: str, column_name: str, limit: int) -> list[Any]:
        sql = text(f"""
            select
                {column_name} as column_value
            from {table_name}
            group by {column_name}
            limit {limit}
        """)
        result = await self.dw_session.execute(sql)
        return [row.column_value for row in result.fetchall()]

    async def get_db_info(self) -> dict[str, str]:
        """
        获取数据仓库信息
        :return: 数据仓库信息
        """
        dialect = self.dw_session.get_bind().dialect.name

        sql = text("select version() as version")
        result = await self.dw_session.execute(sql)
        version = result.scalar()
        return {"dialect": dialect, "version": version}

    async def get_date_info(self) -> dict[str, str]:
        """
        获取日期信息
        :return: 日期信息
        """
        sql = text("select now() as now")
        result = await self.dw_session.execute(sql)
        now = result.scalar()
        return {"date": now.strftime("%Y-%m-%d"), "weekday": now.strftime("%A"), "quarter": now.strftime("%Q")}

    async def validate_sql(self, query):
        await self.dw_session.execute(text(f"explain {query}"))

    async def execute_sql(self, sql):
        result = await self.dw_session.execute(text(sql))
        return [dict(row) for row in result.mappings().fetchall()]


if __name__ == '__main__':
    async def test():
        dw_mysql_client_manager.init()
        async with dw_mysql_client_manager.session_factory() as session:
            repo = DWMySQLRepository(session)
            print(await repo.get_db_info())
            print(await repo.get_column_types("fact_order"))
            print(await repo.get_column_values("dim_product", "category", 10))
            await repo.validate_sql("select 1")
            print("validate ok")
            print(await repo.execute_sql("select 1 as a, 'x' as b"))
        await dw_mysql_client_manager.close()


    asyncio.run(test())
