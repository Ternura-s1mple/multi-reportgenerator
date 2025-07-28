# backend/services/report_graph.py

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
import chromadb
import json
import asyncio
from sentence_transformers import SentenceTransformer

from backend.services.graph_state import GraphState
from backend.services.model_adapters import get_model_adapter, DeepSeekAdapter, QwenApiAdapter
from backend.schemas.report_schemas import StructuredReport, ReportSection, QueryExpansion 
from langchain_core.output_parsers import PydanticOutputParser
from backend.prompts import report_prompts
from backend.config.config import BASE_DIR, settings
import numpy as np


# --- 定义图的节点 ---

async def expand_topic_node(state: GraphState) -> GraphState:
    """节点1: 为不同模型应用不同的JSON输出策略，以稳定生成查询"""
    print(f"---[节点1: 主题扩展] | 收到状态键: {list(state.keys())} ---")
    topic = state['original_topic']
    model_name = state['model_name'] # 这里我们使用从API层传入的模型名

    adapter = get_model_adapter(model_name)

    print(f"    为主题扩展任务选用模型: {model_name}")

    try:
        # --- vvvv 核心修正：应用与节点三相同的 if/else 逻辑 vvvv ---
        if isinstance(adapter, (DeepSeekAdapter, QwenApiAdapter)):
            # **情况A：对于DeepSeek和Qwen API，我们手动精确控制JSON模式**
            print(f"    检测到 {type(adapter).__name__}，手动开启JSON模式。")
            llm = adapter.create_chat_model(
                model_name=model_name, 
                temperature=0.1,
                response_format={'type': 'json_object'} # 手动传入最简单的参数
            )
            parser = PydanticOutputParser(pydantic_object=QueryExpansion)
            prompt_template = ChatPromptTemplate.from_template(
                report_prompts.TOPIC_EXPANDER_PROMPT_TEMPLATE + "\n\n{format_instructions}"
            )
            chain = prompt_template | llm | parser
            response_obj = await chain.ainvoke({
                "topic": topic,
                "format_instructions": parser.get_format_instructions()
            })

        else:
            # **情况B：对于其他模型（如Gemini, 本地vLLM），继续使用标准的 .with_structured_output**
            print(f"    检测到 {type(adapter).__name__}，使用标准 .with_structured_output。")
            llm = adapter.create_chat_model(model_name=model_name, temperature=0.1)
            structured_llm = llm.with_structured_output(QueryExpansion)
            prompt = ChatPromptTemplate.from_template(report_prompts.TOPIC_EXPANDER_PROMPT_TEMPLATE)
            chain = prompt | structured_llm
            response_obj = await chain.ainvoke({"topic": topic})
        # --- ^^^^ 修正结束 ^^^^ ---

        queries = response_obj.queries
        print(f"✅ 成功生成扩展查询 (Rationale: {getattr(response_obj, 'rationale', 'N/A')})")
        if not queries:
            queries = [topic]

    except Exception as e:
        print(f"❌ 生成扩展查询失败: {e}。将使用原始主题作为回退。")
        queries = [topic]

    return {"expanded_queries": queries}



async def retrieve_context_node(state: GraphState) -> GraphState:
    """
    节点2+3: 仿照 find_similar_reports 的成功模式，
             使用 BGE Bi-Encoder + Cross-Encoder Reranker 进行两阶段RAG检索。
    """
    print("---[节点2: 上下文检索 (召回+精排模式)]---")

    knowledge_collection = state.get('knowledge_collection')
    sentence_model = state.get('sentence_model')
    reranker_model = state.get('reranker_model') # 获取重排模型
    topic = state['original_topic'] # 我们用原始主题来做精排

    if not all([knowledge_collection, sentence_model, reranker_model]):
        print("    RAG所需的一个或多个工具未初始化，跳过检索。")
        return {"retrieved_context": "无相关知识库资料。"}

    if knowledge_collection.count() == 0:
        print("    知识库为空，跳过检索。")
        return {"retrieved_context": "知识库中无任何资料。"}

    # --- 第一阶段：召回 (Recall) ---
    # 使用扩展后的查询来做初步筛选，以获得更广泛的候选集
    queries = state['expanded_queries']
    print(f"    [召回] 正在使用 {len(queries)} 个扩展查询进行初步检索...")
    query_embeddings = await asyncio.to_thread(sentence_model.encode, queries)

    # 召回一批可能相关的候选文档 (比如20个)
    recall_results = knowledge_collection.query(
        query_embeddings=query_embeddings.tolist(), 
        n_results=20
    )

    if not recall_results or not recall_results['documents'] or not recall_results['documents'][0]:
        print("    [召回] 未找到任何候选文档。")
        return {"retrieved_context": "在知识库中未找到相关资料。"}

    recalled_documents = recall_results['documents'][0]
    # 去重，防止多个查询召回同一个文档
    unique_documents = list(dict.fromkeys(recalled_documents))
    print(f"    [召回] 初步检索到 {len(unique_documents)} 个不重复的文档块。")

    # --- 第二阶段：精排 (Rerank) ---
    print("--- [精排] ---")

    # 准备 Cross-Encoder 的输入：[(原始主题, 文档1), (原始主题, 文档2), ...]
    pairs = [[topic, doc] for doc in unique_documents]

    print(f"    正在为 {len(pairs)} 个候选文档计算相关度分数...")
    # reranker.predict 是同步的，用 to_thread 运行
    scores = await asyncio.to_thread(reranker_model.predict, pairs)
    print("    分数计算完成。")

    # 将分数与文档内容关联，并按分数从高到低排序
    scored_docs = sorted(zip(scores, unique_documents), key=lambda x: x[0], reverse=True)

    # 应用相似度阈值并提取最终的上下文
    final_context_list = []
    RERANK_THRESHOLD = 0.1 # 您可以根据RAG的效果调整这个阈值
    TOP_K = 5 # 只选择最相关的5个文档块

    print("--- [精排结果过滤] ---")
    for score, doc in scored_docs[:TOP_K]:
        if score > RERANK_THRESHOLD:
            print(f"    - (分数: {score:.4f}) - 相关，保留。")
            final_context_list.append(doc)
        else:
            print(f"    - (分数: {score:.4f}) - 不够相关，忽略。")

    final_context_str = "\n\n---\n\n".join(final_context_list)

    if not final_context_str:
        print("精排后未找到足够相关的上下文。")
        return {"retrieved_context": "在知识库中未找到足够相关的资料。"}

    print(f"精排后选出 {len(final_context_list)} 个文档块，总长度: {len(final_context_str)}字")
    return {"retrieved_context": final_context_str}


async def generate_report_node(state: GraphState) -> GraphState:
    print(f"---[节点3: 最终报告生成] | 收到状态键: {list(state.keys())} ---")
    topic = state['original_topic']
    context = state['retrieved_context']
    model_name = state['model_name']
    template_content = state.get('template_content')

    if template_content:
        formatting_instructions = template_content
    else:
        formatting_instructions = report_prompts.NO_TEMPLATE_INSTRUCTION

    adapter = get_model_adapter(model_name)

    if isinstance(adapter, (DeepSeekAdapter,QwenApiAdapter)):
        print("    检测到DeepSeek模型，手动开启JSON模式。")

        # 创建LLM实例
        llm = adapter.create_chat_model(
            model_name=model_name, 
            temperature=0.7,
            response_format={'type': 'json_object'} 
        )

        # 使用 PydanticOutputParser 
        parser = PydanticOutputParser(pydantic_object=StructuredReport)
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", report_prompts.SYSTEM_INSTRUCTION),
            ("human", report_prompts.FINAL_REPORT_PROMPT_TEMPLATE + "\n\n{format_instructions}")
        ])
        chain = prompt_template | llm | parser

        # 异步调用链
        response_dict = await chain.ainvoke({
            "topic": topic, "context": context,
            "formatting_instructions": formatting_instructions,
            "format_instructions": parser.get_format_instructions(),
        })
        response = StructuredReport.model_validate(response_dict)

    else:
       
        print("    使用 .with_structured_output 方法进行结构化输出...")
        llm = adapter.create_chat_model(model_name=model_name, temperature=0.5)
        structured_llm = llm.with_structured_output(StructuredReport)

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", report_prompts.SYSTEM_INSTRUCTION),
            ("human", report_prompts.FINAL_REPORT_PROMPT_TEMPLATE),
        ])
        prompt_inputs = {"topic": topic, "context": context, "formatting_instructions": formatting_instructions}
        formatted_prompt = prompt_template.invoke(prompt_inputs)
        response = await structured_llm.ainvoke(formatted_prompt)

    print("最终报告已生成。")
    return {"final_report": response}


workflow = StateGraph(GraphState)

# 添加节点
workflow.add_node("expand_topic", expand_topic_node)
workflow.add_node("retrieve_context", retrieve_context_node)
workflow.add_node("generate_report", generate_report_node)

# 定义边的连接关系
workflow.set_entry_point("expand_topic")
workflow.add_edge("expand_topic", "retrieve_context")
workflow.add_edge("retrieve_context", "generate_report")
workflow.add_edge("generate_report", END)

# 编译图
graph = workflow.compile()
print("LangGraph 工作流已编译完成。")