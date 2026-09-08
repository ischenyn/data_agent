from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger
from app.repository.mysql.dw_mysql_repository import DWMySQLRepository


async def execute_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"stage": "执行SQL语句"})

    sql = state["sql"]
    dw_mysql_repository: DWMySQLRepository = runtime.context['dw_mysql_repository']

    try:
        result = await dw_mysql_repository.execute_sql(sql)
        logger.info(f"SQL执行结果: {result}")
        writer({"result": result})
    except Exception as e:
        logger.error(f"SQL执行失败: {e}")
        raise