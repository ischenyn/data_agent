from copy import deepcopy

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


async def filter_table_info(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"stage": "筛选表信息"})

    table_infos = state["table_infos"]
    query = state["query"]

    try:
        prompt = PromptTemplate(template=load_prompt("filter_table_info"),
                                input_variables=["query", "table_infos"])
        out_parser = JsonOutputParser()
        chain = prompt | llm | out_parser

        result = await chain.ainvoke({"query": query, "table_infos": table_infos})

        # 构造 规范化表名 -> {规范化列名 -> 原名},容忍 LLM 输出与原始名称的空白/大小写差异
        normalized_result = {
            _normalize(table_name): {_normalize(col_name): col_name for col_name in columns}
            for table_name, columns in (result or {}).items()
        }

        filtered_table_infos = []
        for table_info in table_infos:
            matched_columns = normalized_result.get(_normalize(table_info['name']))
            if matched_columns is None:
                continue
            kept_columns = [
                column for column in table_info['columns']
                if _normalize(column['name']) in matched_columns
            ]
            if kept_columns:
                # 浅拷贝出新表结构,避免直接修改 state 中的原对象
                new_table_info = deepcopy(table_info)
                new_table_info['columns'] = kept_columns
                filtered_table_infos.append(new_table_info)

        logger.info(f"表格筛选结果: {[t['name'] for t in filtered_table_infos]}")
        return {"table_infos": filtered_table_infos}
    except Exception as e:
        logger.error(f"表格筛选失败: {str(e)}")
        raise
