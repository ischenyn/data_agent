from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def correct_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """
    根据上一次生成的SQL和校验失败的错误信息，让LLM在保持语义不变的前提下，
    修正SQL，使其能够通过校验。
    Args:
        state:
        runtime:

    Returns:

    """
    writer = runtime.stream_writer
    writer({"stage": "校正SQL"})

    query = state['query']
    sql = state['sql']
    error = state['error']
    table_infos = state['table_infos']
    metric_infos = state['metric_infos']
    date_info = state['date_info']
    db_info = state["db_info"]

    try:
        prompt = PromptTemplate(
            template=load_prompt("correct_sql"),
            input_variables=[
                "sql",
                "error",
                "table_infos",
                "metric_infos",
                "query",
                "date_info",
                "db_info"
            ]
        )
        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {
                "table_infos": table_infos,
                "metric_infos": metric_infos,
                "date_info": date_info,
                "db_info": db_info,
                "query": query,
                "sql": sql,
                "error": error
            }
        )

        logger.info(f"校正SQL结果: {result}")
        attempts = state.get("attempts", 0) + 1
        logger.info(f"SQL 纠错第 {attempts} 次")
        return {"sql": result, "attempts": attempts}

    except Exception as e:
        logger.error(f"校正SQL失败: {e}")
        raise
