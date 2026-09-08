from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.add_context import add_context
from app.agent.nodes.column_recall import column_recall
from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.execute_sql import execute_sql
from app.agent.nodes.extract_keywords import extract_keywords
from app.agent.nodes.filter_metric_info import filter_metric_info
from app.agent.nodes.filter_table_info import filter_table_info
from app.agent.nodes.generate_sql import generate_sql
from app.agent.nodes.merge_retrieved_info import merge_retrieved_info
from app.agent.nodes.metric_recall import metric_recall
from app.agent.nodes.validate_sql import validate_sql
from app.agent.nodes.value_recall import value_recall
from app.agent.state import DataAgentState

# SQL 纠错最大次数:超过仍未通过校验则放弃执行,避免 validate↔correct 无限循环
MAX_ATTEMPTS = 3


async def give_up(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """纠错达到上限仍未通过校验,放弃执行,把最终错误留给调用方"""
    writer = runtime.stream_writer
    writer({"stage": "放弃生成SQL", "message": f"SQL 经过 {MAX_ATTEMPTS} 次纠错仍未通过校验", "error": state.get("error")})
    return {}


def route_after_validate(state: DataAgentState) -> str:
    if state.get("error") is None:
        return "execute_sql"
    if state.get("attempts", 0) >= MAX_ATTEMPTS:
        return "give_up"
    return "correct_sql"


graph_builder = StateGraph(state_schema=DataAgentState, context_schema=DataAgentContext)

graph_builder.add_node("extract_keywords", extract_keywords)
graph_builder.add_node("column_recall", column_recall)
graph_builder.add_node("value_recall", value_recall)
graph_builder.add_node("metric_recall", metric_recall)
graph_builder.add_node("merge_retrieved_info", merge_retrieved_info)
graph_builder.add_node("filter_table_info", filter_table_info)
graph_builder.add_node("filter_metric_info", filter_metric_info)
graph_builder.add_node("add_context", add_context)
graph_builder.add_node("generate_sql", generate_sql)
graph_builder.add_node("validate_sql", validate_sql)
graph_builder.add_node("correct_sql", correct_sql)
graph_builder.add_node("execute_sql", execute_sql)
graph_builder.add_node("give_up", give_up)

graph_builder.add_edge(START, "extract_keywords")

graph_builder.add_edge("extract_keywords", "column_recall")
graph_builder.add_edge("extract_keywords", "value_recall")
graph_builder.add_edge("extract_keywords", "metric_recall")

graph_builder.add_edge("column_recall", "merge_retrieved_info")
graph_builder.add_edge("value_recall", "merge_retrieved_info")
graph_builder.add_edge("metric_recall", "merge_retrieved_info")

graph_builder.add_edge("merge_retrieved_info", "filter_table_info")
graph_builder.add_edge("merge_retrieved_info", "filter_metric_info")

graph_builder.add_edge("filter_table_info", "add_context")
graph_builder.add_edge("filter_metric_info", "add_context")

graph_builder.add_edge("add_context", "generate_sql")
graph_builder.add_edge("generate_sql", "validate_sql")

# 校验通过→执行;未通过但未超上限→纠错后重新校验;超上限→放弃
graph_builder.add_conditional_edges(
    "validate_sql",
    route_after_validate,
    {
        "execute_sql": "execute_sql",
        "correct_sql": "correct_sql",
        "give_up": "give_up",
    },
)
graph_builder.add_edge("correct_sql", "validate_sql")

graph_builder.add_edge("execute_sql", END)
graph_builder.add_edge("give_up", END)

graph = graph_builder.compile()