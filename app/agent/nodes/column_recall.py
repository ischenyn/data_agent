import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.recall_utils import merge_scored
from app.agent.state import DataAgentState
from app.core.log import logger

# 单个关键词检索数量上限;最终按实体去重、分数排序后截断到 RECALL_LIMIT
_KEYWORD_LIMIT = 10
RECALL_LIMIT = 20


async def _search_column_by_keyword(embedding_client, column_repository_qdrant, keyword: str):
    embedding = await embedding_client.aembed_query(keyword)
    return await column_repository_qdrant.search(embedding, limit=_KEYWORD_LIMIT, with_score=True)


async def column_recall(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """从向量数据库中召回字段信息(按关键词并行检索,合并去重,取分数最高的一批)"""
    write = runtime.stream_writer
    write({"stage": "召回字段信息"})

    keywords = state["column_keywords"]
    column_repository_qdrant = runtime.context['column_repository_qdrant']
    embedding_client = runtime.context['embedding_client']

    try:
        scored_lists = await asyncio.gather(
            *[_search_column_by_keyword(embedding_client, column_repository_qdrant, keyword)
              for keyword in keywords]
        ) if keywords else []

        # 展平所有关键词的 (payload, score),按实体 id 去重保留最高分,分数降序后截断
        flat: list[tuple[dict, float]] = [item for scored in scored_lists for item in scored]
        retrieved_columns = merge_scored(flat, id_key="id")[:RECALL_LIMIT]

        logger.info(f"字段信息召回成功: {[c['id'] for c in retrieved_columns]}")
        return {"retrieved_columns": retrieved_columns}
    except Exception as e:
        logger.error(f"字段信息召回失败: {str(e)}")
        raise
