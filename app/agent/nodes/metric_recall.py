import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.recall_utils import merge_scored
from app.agent.state import DataAgentState
from app.core.log import logger

# 单个关键词检索数量上限;最终按实体去重、分数排序后截断到 RECALL_LIMIT
_KEYWORD_LIMIT = 10
RECALL_LIMIT = 10


async def _search_metric_by_keyword(embedding_client, metric_repository_qdrant, keyword: str):
    embedding = await embedding_client.aembed_query(keyword)
    return await metric_repository_qdrant.search(embedding, limit=_KEYWORD_LIMIT, with_score=True)


async def metric_recall(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """召回指标(按关键词并行检索,合并去重,取分数最高的一批)"""
    writer = runtime.stream_writer
    writer({"stage": "召回指标"})

    keywords = state['metric_keywords']
    embedding_client = runtime.context['embedding_client']
    metric_repository_qdrant = runtime.context['metric_repository_qdrant']

    try:
        scored_lists = await asyncio.gather(
            *[_search_metric_by_keyword(embedding_client, metric_repository_qdrant, keyword)
              for keyword in keywords]
        ) if keywords else []

        flat: list[tuple[dict, float]] = [item for scored in scored_lists for item in scored]
        retrieved_metrics = merge_scored(flat, id_key="id")[:RECALL_LIMIT]

        logger.info(f"指标信息召回成功: {[m['id'] for m in retrieved_metrics]}")
        return {"retrieved_metrics": retrieved_metrics}
    except Exception as e:
        logger.error(f"指标信息召回失败: {str(e)}")
        raise
