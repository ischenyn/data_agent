from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.models.es.value_info_es import ValueInfoES
from app.prompt.prompt_loader import load_prompt
from app.repository.es.value_es_repository import ValueESRepository


async def value_recall(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """
    召回字段值
    Args:
        state:
        runtime:

    Returns:

    """
    write = runtime.stream_writer
    write({"stage": "召回字段值"})

    query = state['query']
    keywords = state['keywords']
    value_es_repository: ValueESRepository = runtime.context["value_es_repository"]

    try:
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_value_recall"),
                                input_variables=["query"])
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke({"query": query})
        keywords = list(set(keywords + result))

        values_map: dict[str, ValueInfoES] = {}
        for keyword in keywords:
            values =  await value_es_repository.query(keyword, score_threshold=0.6, limit=5)
            for value in values:
                if value["id"] not in values_map:
                    values_map[value["id"]] = value

        retrieved_values = list(values_map.values())
        logger.info(f"召回字段值成功: {values_map.keys()}")
        return {"retrieved_values": retrieved_values}
    except Exception as e:
        logger.error(f"召回字段值失败: {str(e)}")
        raise
