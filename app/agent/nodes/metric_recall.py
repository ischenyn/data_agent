from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.clients.embedding_client import LocalEmbeddingClient
from app.core.log import logger
from app.models.qdrant.metric_info_qdrant import MetricInfoQdrant
from app.prompt.prompt_loader import load_prompt
from app.repository.qdrant.metric_repository_qdrant import MetricQdrantRepository


async def metric_recall(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """
    召回指标
    Args:
        state:
        runtime:

    Returns:

    """
    writer = runtime.stream_writer
    writer({"stage": "召回指标"})

    keywords = state['keywords']
    query = state['query']
    embedding_client: LocalEmbeddingClient = runtime.context['embedding_client']
    metric_repository_qdrant: MetricQdrantRepository = runtime.context['metric_repository_qdrant']

    try:
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_metric_recall"),
                                input_variables=["query"])
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke({"query": query})
        keywords = list(set(keywords + result))

        metrics_map: dict[str, MetricInfoQdrant] = {}
        for keyword in keywords:
            embedding = await embedding_client.aembed_query(keyword)
            metrics = await metric_repository_qdrant.search(embedding)
            for metric in metrics:
                if metric['id'] not in metrics_map:
                    metrics_map[metric['id']] = metric

        retrieved_metrics = list(metrics_map.values())
        logger.info(f"指标信息召回成功: {metrics_map.keys()}")
        return {"retrieved_metrics": retrieved_metrics}
    except Exception as e:
        logger.error(f"指标信息召回失败: {str(e)}")
        raise
