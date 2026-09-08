from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, TableInfoState, MetricInfoState, ColumnInfoState
from app.core.log import logger
from app.models.mysql.column_info_mysql import ColumnInfoMySQL
from app.models.mysql.table_info_mysql import TableInfoMySQL
from app.models.qdrant.column_info_qdrant import ColumnInfoQdrant
from app.models.qdrant.metric_info_qdrant import MetricInfoQdrant


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


def convert_column_info_from_qdrant_to_state(column_info: ColumnInfoQdrant) -> ColumnInfoState:
    return ColumnInfoState(
        name=column_info['name'],
        type=column_info['type'],
        role=column_info['role'],
        description=column_info['description'],
        alias=column_info['alias'],
        examples=column_info['examples']
    )


def convert_column_info_from_mysql_to_state(column_info: ColumnInfoMySQL) -> ColumnInfoState:
    return ColumnInfoState(
        name=column_info.name,
        type=column_info.type,
        role=column_info.role,
        description=column_info.description,
        alias=column_info.alias,
        examples=column_info.examples
    )


def convert_table_info_from_mysql_to_state(table_info: TableInfoMySQL,
                                           column_states: list[ColumnInfoState]) -> TableInfoState:
    return TableInfoState(
        name=table_info.name,
        role=table_info.role,
        description=table_info.description,
        columns=column_states
    )


def convert_metric_info_from_qdrant_to_state(metric_info: MetricInfoQdrant) -> MetricInfoState:
    return MetricInfoState(
        name=metric_info['name'],
        description=metric_info['description'],
        alias=metric_info['alias']
    )


async def merge_retrieved_info(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """
    把三路召回结果合并成"按表组织的完整 schema + 指标"。

    相比逐条查询 MySQL(原 N+1),这里把所有缺失的字段/表/主外键一次性批量查出,
    避免在线问答中产生大量串行数据库往返。
    """
    writer = runtime.stream_writer
    writer({"stage": "合并召回信息"})

    retrieved_columns = state["retrieved_columns"]
    retrieved_values = state["retrieved_values"]
    retrieved_metrics = state["retrieved_metrics"]
    meta_mysql_repository = runtime.context['meta_mysql_repository']

    table_infos: list[TableInfoState] = []
    metric_infos: list[MetricInfoState] = []

    # 1. 用字段召回结果打底:"字段编号 → 字段信息"
    id_to_column_map: dict[str, ColumnInfoQdrant] = {column['id']: column for column in retrieved_columns}

    # 2. 找出所有"字段召回没覆盖、但取值/指标引用了"的字段编号,一次批量查 MySQL
    extra_column_ids: list[str] = []
    for retrieved_value in retrieved_values:
        column_id = retrieved_value['column_id']
        if column_id not in id_to_column_map and column_id not in extra_column_ids:
            extra_column_ids.append(column_id)
    for retrieved_metric in retrieved_metrics:
        for column_id in retrieved_metric['relevant_columns']:
            if column_id not in id_to_column_map and column_id not in extra_column_ids:
                extra_column_ids.append(column_id)

    if extra_column_ids:
        extra_columns = await meta_mysql_repository.get_columns_by_ids(extra_column_ids)
        for column_info in extra_columns:
            id_to_column_map[column_info.id] = convert_column_info_from_mysql_to_qdrant(column_info)

    # 3. 把取值追加到对应字段的样例里(命中已掌握字段的直接追加;此前缺失的字段已在第2步补全)
    for retrieved_value in retrieved_values:
        column_id = retrieved_value['column_id']
        value = retrieved_value['value']
        column_payload = id_to_column_map.get(column_id)
        if column_payload is not None and value not in (column_payload.get('examples') or []):
            column_payload['examples'] = (column_payload.get('examples') or []) + [value]

    # 4. 按所属表分组
    table_to_columns_map: dict[str, list[ColumnInfoQdrant]] = {}
    for column in id_to_column_map.values():
        table_to_columns_map.setdefault(column['table_id'], []).append(column)

    # 5. 批量查表信息与所有表的主键外键
    table_id2info = {
        t.id: t for t in await meta_mysql_repository.get_tables_by_ids(list(table_to_columns_map.keys()))
    }
    table_id2key_columns = await meta_mysql_repository.get_key_columns_by_table_ids(list(table_to_columns_map.keys()))

    for table_id, columns in table_to_columns_map.items():
        table_info = table_id2info.get(table_id)
        if table_info is None:
            logger.warning(f"表 {table_id} 在元数据库中不存在,跳过")
            continue
        column_states: list[ColumnInfoState] = []
        column_state_ids: list[str] = []
        for column in columns:
            column_states.append(convert_column_info_from_qdrant_to_state(column))
            column_state_ids.append(column['id'])

        # 补全主键外键(可能来自"按表分组"后仍未出现在列集合里的关联列)
        for key_column in table_id2key_columns.get(table_id, []):
            if key_column.id not in column_state_ids:
                column_states.append(convert_column_info_from_mysql_to_state(key_column))

        table_infos.append(convert_table_info_from_mysql_to_state(table_info, column_states))

    # 6. 把召回到的指标转换为最终 MetricInfoState
    for metric in retrieved_metrics:
        metric_infos.append(convert_metric_info_from_qdrant_to_state(metric))

    logger.info(f"召回信息合并成功: 表 {[t['name'] for t in table_infos]}")
    return {"table_infos": table_infos, "metric_infos": metric_infos}
