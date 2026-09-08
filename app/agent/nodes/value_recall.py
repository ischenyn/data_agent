import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.recall_utils import dedupe_preserving_order
from app.agent.state import DataAgentState
from app.core.log import logger

# 单个关键词 ES 召回数量上限;ES 已按 BM25 相关度降序返回,合并后截断到 RECALL_LIMIT
_KEYWORD_LIMIT = 10
RECALL_LIMIT = 20


async def _query_value_by_keyword(value_es_repository, keyword: str):
    return await value_es_repository.query(keyword, limit=_KEYWORD_LIMIT)


async def value_recall(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """召回字段取值(按关键词并行查 ES,结果已按相关度降序,合并去重后截断)"""
    write = runtime.stream_writer
    write({"stage": "召回字段值"})

    keywords = state['value_keywords']
    value_es_repository = runtime.context["value_es_repository"]

    try:
        keyword_results = await asyncio.gather(
            *[_query_value_by_keyword(value_es_repository, keyword) for keyword in keywords]
        ) if keywords else []

        # ES 每个关键词结果已按 _score 降序,按文档 id 去重保持顺序即可
        flat: list[dict] = [value for results in keyword_results for value in results]
        retrieved_values = dedupe_preserving_order(flat, id_key="id")[:RECALL_LIMIT]

        logger.info(f"召回字段值成功: {len(retrieved_values)} 条")
        return {"retrieved_values": retrieved_values}
    except Exception as e:
        logger.error(f"召回字段值失败: {str(e)}")
        raise
