from typing import TypedDict, Any

from app.models.es.value_info_es import ValueInfoES
from app.models.qdrant.column_info_qdrant import ColumnInfoQdrant
from app.models.qdrant.metric_info_qdrant import MetricInfoQdrant


class MetricInfoState(TypedDict):
    name: str  # 指标名称
    description: str  # 指标描述
    alias: list[str]  # 指标别名


class ColumnInfoState(TypedDict):
    name: str  # 字段名称
    type: str  # 字段类型
    role: str  # 字段角色（primary_key/foreign_key/dimension/measure）
    description: str  # 字段描述
    alias: list[str]  # 字段别名
    examples: list[Any]  # 字段示例


class TableInfoState(TypedDict):
    name: str  # 表名称
    role: str  # 表角色（fact/dim）
    description: str  # 表描述
    columns: list[ColumnInfoState]  # 字段信息


class DateInfoState(TypedDict):
    date: str  # 日期
    weekday: str  # 星期
    quarter: str  # 季度


class DBInfoState(TypedDict):
    dialect: str  # 数据库方言
    version: str  # 数据库版本


class DataAgentState(TypedDict):
    query: str  # 用户的原始问题

    # 关键词列表，由 extract_keywords 一次生成，分别驱动三路召回
    column_keywords: list[str]  # 字段概念关键词（用于 Qdrant 字段召回）
    metric_keywords: list[str]  # 指标概念关键词（用于 Qdrant 指标召回）
    value_keywords: list[str]  # 取值候选关键词（用于 ES 取值召回）

    retrieved_metrics: list[MetricInfoQdrant]  # 召回的指标信息（原始）
    retrieved_columns: list[ColumnInfoQdrant]  # 召回的字段信息（原始）
    retrieved_values: list[ValueInfoES]  # 召回的字段值信息（原始）

    table_infos: list[TableInfoState]  # 合并后、按表组织的信息
    metric_infos: list[MetricInfoState]  # 合并后的指标信息

    date_info: DateInfoState  # 当前的日期信息
    db_info: DBInfoState  # 数据库信息

    sql: str  # 生成的SQL语句
    error: str  # 校验SQL语句的错误信息（没有错误则为 None）
    attempts: int  # SQL 纠错尝试次数（达到上限仍未通过校验则放弃）
