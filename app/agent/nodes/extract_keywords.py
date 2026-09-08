import json

import jieba.analyse
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt

# 每类关键词的数量上限,控制后续检索成本
_KEYWORD_LIMIT = 8


def _is_number(word: str) -> bool:
    """判断词是否为纯数字(年份/数量等单独数字对语义召回无意义,过滤掉)。

    只过滤"去掉数字与少量符号后没有剩余字符"的词,保留"1月""2025年"这类
    带语义的混合词。
    """
    if not word:
        return True
    stripped = "".join(ch for ch in word if ch.isdigit() or ch in ".,%+-")
    return len(stripped) == len(word)


async def extract_keywords(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """从查询中提取三类关键词,一次 LLM 调用完成,分别驱动字段/指标/取值三路召回。

    返回:
        column_keywords: 字段概念关键词(用于 Qdrant 字段召回)
        metric_keywords: 指标概念关键词(用于 Qdrant 指标召回)
        value_keywords: 取值候选关键词(用于 ES 取值召回)
    """
    write = runtime.stream_writer
    write({"stage": "抽取关键词"})

    query = state["query"]

    # 1. jieba 分词打底(无 LLM 依赖的保底召回词)
    allow_pos = (
        "n", "nr", "ns", "nt", "nz", "v", "vn", "a", "an", "eng", "i", "l",
    )
    jieba_keywords = [w for w in jieba.analyse.extract_tags(query, withWeight=False, allowPOS=allow_pos)
                      if not _is_number(w)]
    logger.info(f"jieba 基础关键词：{jieba_keywords}")

    # 2. 一次 LLM 调用,产出三类关键词
    column_keywords, metric_keywords, value_keywords = [], [], []
    try:
        prompt = PromptTemplate(
            template=load_prompt("extract_keywords"),
            input_variables=["query"],
        )
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke({"query": query})
        if isinstance(result, dict):
            column_keywords = result.get("column_keywords") or []
            metric_keywords = result.get("metric_keywords") or []
            value_keywords = result.get("value_keywords") or []
    except Exception as e:
        # LLM 失败不阻断流程:三类全部退回 jieba 基础词,保证后续召回仍可执行
        logger.warning(f"LLM 关键词扩展失败,退回 jieba 基础词: {e}")
        column_keywords = metric_keywords = value_keywords = []

    # 3. jieba 基础词并入三类做保底(防 LLM 漏召回或分类错误),去重后截断
    column_keywords = list(dict.fromkeys(jieba_keywords + column_keywords))[:_KEYWORD_LIMIT]
    metric_keywords = list(dict.fromkeys(jieba_keywords + metric_keywords))[:_KEYWORD_LIMIT]
    value_keywords = list(dict.fromkeys(jieba_keywords + value_keywords))[:_KEYWORD_LIMIT]

    logger.info(f"关键词提取: column={column_keywords}, metric={metric_keywords}, value={value_keywords}")
    return {
        "column_keywords": column_keywords,
        "metric_keywords": metric_keywords,
        "value_keywords": value_keywords,
    }
