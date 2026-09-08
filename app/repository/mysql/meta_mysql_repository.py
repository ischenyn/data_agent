from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mysql.column_info_mysql import ColumnInfoMySQL
from app.models.mysql.column_metric_mysql import ColumnMetricMySQL
from app.models.mysql.metric_info_mysql import MetricInfoMySQL
from app.models.mysql.table_info_mysql import TableInfoMySQL


class MetaMySQLRepository:
    def __init__(self, meta_session: AsyncSession):
        self.session = meta_session

    async def delete_all(self):
        """清空四张元数据表(全量重建用),顺序先子表后主表,自成一个事务。
        用 DELETE 而非 TRUNCATE:TRUNCATE 是 DDL 会隐式提交,不适合放在事务里。
        """
        async with self.session.begin():
            for table_name in ('column_metric', 'column_info', 'metric_info', 'table_info'):
                await self.session.execute(text(f"DELETE FROM {table_name}"))

    async def save_table_infos(self, table_infos: list[TableInfoMySQL]):
        self.session.add_all(table_infos)

    async def save_column_infos(self, column_infos: list[ColumnInfoMySQL]):
        self.session.add_all(column_infos)

    async def save_metric_infos(self, metric_infos: list[MetricInfoMySQL]):
        self.session.add_all(metric_infos)

    async def save_column_metrics(self, column_metrics: list[ColumnMetricMySQL]):
        self.session.add_all(column_metrics)

    async def get_column_by_id(self, column_id: str) -> ColumnInfoMySQL | None:
        return await self.session.get(ColumnInfoMySQL, column_id)

    async def get_columns_by_ids(self, column_ids: list[str]) -> list[ColumnInfoMySQL]:
        """批量查询字段(在线召回合并阶段用,替代 N+1 单查)"""
        if not column_ids:
            return []
        query = select(ColumnInfoMySQL).where(ColumnInfoMySQL.id.in_(column_ids))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_table_by_id(self, table_id) -> TableInfoMySQL | None:
        return await self.session.get(TableInfoMySQL, table_id)

    async def get_tables_by_ids(self, table_ids: list[str]) -> list[TableInfoMySQL]:
        """批量查询表(在线召回合并阶段用,替代 N+1 单查)"""
        if not table_ids:
            return []
        query = select(TableInfoMySQL).where(TableInfoMySQL.id.in_(table_ids))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_key_columns_by_table_id(self, table_id) -> list[ColumnInfoMySQL]:
        query = select(ColumnInfoMySQL).where(
            ColumnInfoMySQL.table_id == table_id,
            ColumnInfoMySQL.role.in_(('primary_key', 'foreign_key')),
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_key_columns_by_table_ids(self, table_ids: list[str]) -> dict[str, list[ColumnInfoMySQL]]:
        """批量查询多张表的主键/外键,返回 {table_id: [columns]}"""
        if not table_ids:
            return {}
        query = select(ColumnInfoMySQL).where(
            ColumnInfoMySQL.table_id.in_(table_ids),
            ColumnInfoMySQL.role.in_(('primary_key', 'foreign_key')),
        )
        result = await self.session.execute(query)
        key_columns = list(result.scalars().all())
        table_map: dict[str, list[ColumnInfoMySQL]] = {}
        for column in key_columns:
            table_map.setdefault(column.table_id, []).append(column)
        return table_map
