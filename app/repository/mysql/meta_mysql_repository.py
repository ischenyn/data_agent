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

    async def get_table_by_id(self, table_id) -> TableInfoMySQL | None:
        return await self.session.get(TableInfoMySQL, table_id)

    async def get_key_columns_by_table_id(self, table_id) -> list[ColumnInfoMySQL]:
        query = select(ColumnInfoMySQL).where(
            ColumnInfoMySQL.table_id == table_id,
            ColumnInfoMySQL.role.in_(('primary_key', 'foreign_key')),
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
