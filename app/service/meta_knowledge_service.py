import asyncio
import hashlib
from pathlib import Path

from app.clients.embedding_client import LocalEmbeddingClient
from app.config.config_loader import load_config
from app.config.meta_config import MetaConfig, TableConfig, MetricConfig
from app.core.log import logger
from app.models.es.value_info_es import ValueInfoES
from app.models.mysql.column_info_mysql import ColumnInfoMySQL
from app.models.mysql.column_metric_mysql import ColumnMetricMySQL
from app.models.mysql.metric_info_mysql import MetricInfoMySQL
from app.models.mysql.table_info_mysql import TableInfoMySQL
from app.models.qdrant.column_info_qdrant import ColumnInfoQdrant
from app.models.qdrant.metric_info_qdrant import MetricInfoQdrant
from app.repository.es.value_es_repository import ValueESRepository
from app.repository.mysql.dw_mysql_repository import DWMySQLRepository
from app.repository.mysql.meta_mysql_repository import MetaMySQLRepository
from app.repository.qdrant.column_repository_qdrant import ColumnQdrantRepository
from app.repository.qdrant.metric_repository_qdrant import MetricQdrantRepository


def convert_column_info_from_mysql_to_qdrant(column_info: ColumnInfoMySQL):
    return ColumnInfoQdrant(
        id=column_info.id,
        name=column_info.name,
        type=column_info.type,
        role=column_info.role,
        examples=column_info.examples,
        description=column_info.description,
        alias=column_info.alias,
        table_id=column_info.table_id
    )


def convert_metric_info_from_mysql_to_qdrant(metric_info):
    return MetricInfoQdrant(
        id=metric_info.id,
        name=metric_info.name,
        description=metric_info.description,
        relevant_columns=metric_info.relevant_columns,
        alias=metric_info.alias
    )


class MetaKnowledgeService:
    def __init__(self,
                 dw_mysql_repository: DWMySQLRepository,
                 meta_mysql_repository: MetaMySQLRepository,
                 embedding_client: LocalEmbeddingClient,
                 column_repository_qdrant: ColumnQdrantRepository,
                 metric_repository_qdrant: MetricQdrantRepository,
                 value_es_repository: ValueESRepository
                 ):
        self.dw_mysql_repository = dw_mysql_repository
        self.meta_mysql_repository = meta_mysql_repository
        self.embedding_client = embedding_client
        self.column_repository_qdrant = column_repository_qdrant
        self.metric_repository_qdrant = metric_repository_qdrant
        self.value_es_repository = value_es_repository

    async def build_meta_knowledge(self, path: Path):
        # 0. 全量重建:先清空 MySQL 元数据表、Qdrant collection、ES 索引,
        #    保证本次构建结果与 meta_config.yaml 完全一致,脚本可重复执行。
        logger.info('开始全量重建:清空 MySQL 元数据表 / Qdrant / ES')
        await self.meta_mysql_repository.delete_all()
        await self.column_repository_qdrant.reset()
        await self.metric_repository_qdrant.reset()
        await self.value_es_repository.reset()

        # 1. 拿到配置文件的路径,把 yaml 内容读成一个 Python 能用的对象。
        logger.info('加载元数据配置文件')
        meta_config = load_config(config_file=path, schema_cls=MetaConfig)

        # 2. 检查这份配置
        table_count = column_count = value_count = metric_count = 0
        # 2.1 "表"这部分是不是有内容,如果有,依次做三件事,而且这三件事的先后顺序是硬性要求:
        logger.info('保存表信息和字段信息到meta数据库')
        if meta_config.tables:
            table_infos, column_infos = await self._save_tables_to_meta_db(meta_config.tables)
            await self._sync_columns_to_qdrant(column_infos)
            value_count = await self._sync_values_to_es(table_infos, column_infos, meta_config.tables)
            table_count = len(table_infos)
            column_count = len(column_infos)
        # 2.2 "指标"这部分是不是有内容
        if meta_config.metrics:
            metric_infos = await self._save_metrics_to_meta_db(meta_config.metrics)
            await self._sync_metrics_to_qdrant(metric_infos)
            metric_count = len(metric_infos)

        # 3. 汇总统计日志
        logger.info(
            f'构建完成: 表 {table_count} 张, 字段 {column_count} 个, '
            f'取值 {value_count} 条, 指标 {metric_count} 个'
        )

    async def _save_tables_to_meta_db(self, tables: list[TableConfig]):
        table_infos = []
        column_infos = []

        for table in tables:
            table_info = TableInfoMySQL(
                id=table.name,
                name=table.name,
                role=table.role,
                description=table.description
            )
            column_types = await self.dw_mysql_repository.get_column_types(table.name)
            # schema 对账:yaml 中配置的列必须真实存在于数仓表,缺列直接报错,避免后续 KeyError
            missing_columns = [column.name for column in table.columns if column.name not in column_types]
            if missing_columns:
                raise ValueError(
                    f"表 {table.name} 中以下列在数仓中不存在,请检查 meta_config.yaml: {missing_columns}"
                )
            for column in table.columns:
                column_info = ColumnInfoMySQL(
                    id=f"{table.name}.{column.name}",
                    name=column.name,
                    type=column_types[column.name],
                    role=column.role,
                    description=column.description,
                    examples=await self.dw_mysql_repository.get_column_values(table_name=table.name,
                                                                              column_name=column.name, limit=10),
                    alias=column.alias,
                    table_id=table.name,
                )
                column_infos.append(column_info)
            table_infos.append(table_info)
        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.save_table_infos(table_infos)
            await self.meta_mysql_repository.save_column_infos(column_infos)
        return table_infos, column_infos

    async def _sync_columns_to_qdrant(self, column_infos):
        """
        1. 确认 Qdrant 那边"存字段"的仓库已经建好了。
        2. 准备一个空篮子,用来装"待处理的记录",每条记录将来要有:
        一个身份编号、一段用来生成向量的文字、一份要存的完整信息。
        3. 对每一个已经存进 MySQL 的字段:
           - 把这个字段转换成"能存进 Qdrant 的那种纯数据格式"。
           - 往篮子里放一条记录:文字是这个字段的名字,信息是刚转换好的那份。
           - 再放一条:文字是这个字段的描述,信息还是同一份。
           - 对这个字段的每一个别名:再放一条,文字是这个别名,信息还是同一份。
        4. 篮子装满之后,把它切成一批一批(比如每批20条)。对每一批:
           - 只取出这一批里"要生成向量的文字"部分,一次性交给 embedding 服务。
           - 拿回这一批对应的向量,按原来的顺序收好。
        5. 现在篮子里每条记录都能配上一个向量了。分别取出所有的"身份编号"、所有的"向量"、所有的"完整信息",三份并排的清单。
        6. 把这三份清单一起交给 Qdrant 仓库的写入方法,让它存进去。
        Args:
            column_infos:

        Returns:

        """
        await self.column_repository_qdrant.ensure_collection()
        records = []
        for column_info in column_infos:
            payload = convert_column_info_from_mysql_to_qdrant(column_info)
            # id 采用确定性格式(实体id + 向量来源),保证重建时可覆盖、可追溯
            records.append(
                {
                    'id': f"{column_info.id}::name",
                    'text': column_info.name,
                    'payload': payload
                }
            )
            records.append(
                {
                    'id': f"{column_info.id}::desc",
                    'text': column_info.description,
                    'payload': payload
                }
            )
            for alia in payload['alias']:
                records.append(
                    {
                        'id': f"{column_info.id}::alias:{alia}",
                        'text': alia,
                        'payload': payload
                    }
                )
        ids, embeddings, payloads = await self._embed_records(records)

        await self.column_repository_qdrant.upsert(ids=ids, embeddings=embeddings, payloads=payloads, batch_size=10)

    async def _embed_records(self, records: list[dict]) -> tuple[list, list, list]:
        embeddings = []
        batch_size = 20
        for i in range(0, len(records), batch_size):
            batch_records = records[i: i + batch_size]
            batch_texts = [record['text'] for record in batch_records]
            batch_embeddings = await self.embedding_client.aembed_documents(batch_texts)
            embeddings.extend(batch_embeddings)

        ids = [record['id'] for record in records]
        payloads = [record['payload'] for record in records]
        return ids, embeddings, payloads

    async def _sync_values_to_es(self, table_infos: list[TableInfoMySQL], column_infos: list[ColumnInfoMySQL],
                                 tables: list[TableConfig]) -> int:
        """
        1. 确认 ES 那边的索引已经建好了。
        2. 建第一张对照表:"表的编号 → 表的名字"(扫一遍已经存好的表对象)。
        3. 建第二张对照表:"字段的编号 → 要不要同步"(扫一遍原始 yaml 配置里"表→字段"这层嵌套结构)。
        4. 准备一个空篮子,用来装"待存入 ES 的记录"。
        5. 对每一个已经存进 MySQL 的字段对象:
           - 查第一张对照表,拿到它所属表的名字。
           - 查第二张对照表,判断这个字段要不要同步。
           - 如果不需要,跳过,处理下一个字段。
           - 如果需要:去数仓问这个字段全部真实取值(最多1万条),把每一个值包装成一条记录(带上值本身、字段编号、字段名、表编号、表名、类型等信息),放进篮子里。
        6. 所有字段都处理完之后,把篮子里的所有记录,一次性交给 ES 仓库存进去。
        Args:
            table_infos:
            column_infos:
            tables:

        Returns:
            int: 成功写入 ES 的取值记录条数

        """
        await self.value_es_repository.ensure_index()

        table_id2name = {}
        for table_info in table_infos:
            table_id2name[table_info.id] = table_info.name

        column_id2sync = {}
        for table in tables:
            for column in table.columns:
                column_id2sync[f"{table.name}.{column.name}"] = column.sync

        # 先并行从数仓拉取所有需要同步字段的真实取值(保持列顺序)
        sync_columns = [column_info for column_info in column_infos if column_id2sync.get(column_info.id)]
        column_values_list = await asyncio.gather(
            *[
                self.dw_mysql_repository.get_column_values(table_name=table_id2name[column_info.table_id],
                                                           column_name=column_info.name,
                                                           limit=10000)
                for column_info in sync_columns
            ]
        )

        records = []
        for column_info, column_values in zip(sync_columns, column_values_list):
            table_name = table_id2name[column_info.table_id]
            for column_value in column_values:
                # id 用 md5,避免取值含特殊字符(如点号)导致 id 不可靠或超长
                value_id = hashlib.md5(
                    f"{table_name}.{column_info.name}.{column_value}".encode("utf-8")
                ).hexdigest()
                records.append(
                    ValueInfoES(
                        id=value_id,
                        value=column_value,
                        type=column_info.type,
                        column_id=column_info.id,
                        column_name=column_info.name,
                        table_id=column_info.table_id,
                        table_name=table_name
                    )
                )
        await self.value_es_repository.batch_index(records)
        return len(records)

    async def _save_metrics_to_meta_db(self, metrics: list[MetricConfig]):
        """
        1. 准备两个空篮子:一个装"指标记录",一个装"指标-字段关联记录"。
        2. 对配置里的每一个指标:
           - 照抄配置里的信息,造一条指标记录,放进第一个篮子。
           - 对这个指标关联的每一个字段编号:造一条"这个字段属于这个指标"的关联记录,放进第二个篮子。
        3. 两个篮子都装满之后,开一个事务,把两个篮子分别存进 meta 库。
        4. 把"指标记录"这个篮子返回出去(下一步 _sync_metrics_to_qdrant 要用)。
        Args:
            metrics:

        Returns:
        """
        metric_infos = []
        metric_columns_infos = []
        for metric in metrics:
            metrics_info = MetricInfoMySQL(
                id=metric.name,
                name=metric.name,
                description=metric.description,
                relevant_columns=metric.relevant_columns,
                alias=metric.alias
            )
            for relevant_column in metric.relevant_columns:
                metric_columns_info = ColumnMetricMySQL(
                    column_id=relevant_column,
                    metric_id=metric.name
                )
                metric_columns_infos.append(metric_columns_info)
            metric_infos.append(metrics_info)

        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.save_metric_infos(metric_infos)
            await self.meta_mysql_repository.save_column_metrics(metric_columns_infos)

        return metric_infos

    async def _sync_metrics_to_qdrant(self, metric_infos: list[MetricInfoMySQL]):
        await self.metric_repository_qdrant.ensure_collection()
        records = []
        for metric_info in metric_infos:
            payload = convert_metric_info_from_mysql_to_qdrant(metric_info)
            records.append(
                {
                    'id': f"{metric_info.id}::name",
                    'text': metric_info.name,
                    'payload': payload
                }
            )
            records.append(
                {
                    'id': f"{metric_info.id}::desc",
                    'text': metric_info.description,
                    'payload': payload
                }
            )
            for alia in metric_info.alias:
                records.append(
                    {
                        'id': f"{metric_info.id}::alias:{alia}",
                        'text': alia,
                        'payload': payload
                    }
                )

        ids, embeddings, payloads = await self._embed_records(records)

        await self.metric_repository_qdrant.upsert(ids=ids, embeddings=embeddings, payloads=payloads, batch_size=10)
