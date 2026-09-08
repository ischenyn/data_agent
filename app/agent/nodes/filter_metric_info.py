from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


def _normalize(name: str) -> str:
    """规范化名称,避免 LLM 输出与原始名称在空白/大小写上不一致导致匹配失败"""
    return name.strip().lower()


async def filter_metric_info(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """
    筛选指标信息
    Args:
        state:
        runtime:

    Returns:

    """
    writer = runtime.stream_writer
    writer({"stage": "筛选指标信息"})

    metric_infos = state['metric_infos']
    query = state['query']

    try:
        prompt = PromptTemplate(template=load_prompt("filter_metric_info"),
                                input_variables=["query", "metric_infos"])
        out_parser = JsonOutputParser()
        chain = prompt | llm | out_parser

        result = await chain.ainvoke({"query": query, "metric_infos": metric_infos})

        normalized_result = {_normalize(name) for name in (result or [])}

        filtered_metric_infos = [
            metric_info for metric_info in metric_infos
            if _normalize(metric_info['name']) in normalized_result
        ]

        logger.info(f"指标筛选结果: {[m['name'] for m in filtered_metric_infos]}")
        return {"metric_infos": filtered_metric_infos}

    except Exception as e:
        logger.error(f"指标筛选失败: {str(e)}")
        raise
