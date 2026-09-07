from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.models.qdrant.column_info_qdrant import ColumnInfoQdrant
from app.prompt.prompt_loader import load_prompt


async def column_recall(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """
    从向量数据库中召回列信息
    Args:
        state:
        runtime:

    Returns:

    """
    write = runtime.stream_writer
    write({"stage": "召回字段信息"})

    keywords = state["keywords"]
    query = state["query"]
    column_repository_qdrant = runtime.context['column_repository_qdrant']
    embedding_client = runtime.context['embedding_client']

    try:
        prompt =  PromptTemplate(
            template=load_prompt("extend_keywords_for_column_recall"),
            input_variables=["query"]
        )
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke({"query": query})

        keywords = list(set(keywords + result))
        columns_map: dict[str, ColumnInfoQdrant] = {}
        for keyword in keywords:
            embedding = await embedding_client.aembed_query(keyword)
            columns = await column_repository_qdrant.search(embedding)
            for column in columns:
                if column['id'] not in columns_map:
                    columns_map[column['id']] = column

        retrieved_columns = list(columns_map.values())

        logger.info(f"字段信息召回成功: {columns_map.keys()}")

        return {"retrieved_columns": retrieved_columns}
    except Exception as e:
        logger.error(f"字段信息召回失败: {str(e)}")
        raise

if __name__ == '__main__':
    import asyncio
    from app.clients.embedding_client import embedding_client_manager
    from app.clients.qdrant_client_manager import qdrant_client_manager
    from app.repository.qdrant.column_repository_qdrant import ColumnQdrantRepository

    class FakeRuntime:
        stream_writer = staticmethod(lambda x: print("STREAM:", x))
        def __init__(self, context):
            self.context = context

    async def test():
        embedding_client_manager.init()
        qdrant_client_manager.init()
        context = {
            'column_repository_qdrant': ColumnQdrantRepository(qdrant_client_manager.client),
            'embedding_client': embedding_client_manager.client,
        }
        state = DataAgentState(query="统计一下华东地区的销售额", keywords=["华东", "地区", "销售额"])
        result = await column_recall(state, FakeRuntime(context))
        for col in result["retrieved_columns"]:
            print(col['id'], col['description'])

        await qdrant_client_manager.close()

    asyncio.run(test())
