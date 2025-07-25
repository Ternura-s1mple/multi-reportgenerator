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
    """节点2: 从本地知识库进行RAG检索"""
    print(f"---[节点2: 上下文检索] | 收到状态键: {list(state.keys())} ---")

    knowledge_collection = state.get('knowledge_collection')
    sentence_model = state.get('sentence_model')

    if not knowledge_collection or not sentence_model:
        print("知识库未初始化，跳过检索。")
        return {"retrieved_context": "无相关知识库资料。"}

    queries = state['expanded_queries']
    print(f"正在使用查询进行检索: {queries}")
    embeddings = await asyncio.to_thread(sentence_model.encode, queries)#sentence_model.encode 是同步的，用 to_thread 在异步环境中运行

    #从新的知识库集合中查询
    results = knowledge_collection.query(
        query_embeddings=embeddings, 
        n_results=5 # 可以调整检索出的文档块数量
    )

    context_list = results.get('documents', [[]])[0]
    context_str = "\n\n---\n\n".join(context_list)

    print(f"检索到的知识库上下文长度: {len(context_str)}字")
    return {"retrieved_context": context_str or "在本地知识库中未找到相关资料。"}


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

    # --- vvvv 核心修改：在这里进行判断和特殊处理 vvvv ---
    if isinstance(adapter, (DeepSeekAdapter,QwenApiAdapter)):
        # **情况A：对于DeepSeek，我们手动控制JSON模式**
        print("    检测到DeepSeek模型，手动开启JSON模式。")

        # 1. 创建LLM实例，并手动传入 response_format
        llm = adapter.create_chat_model(
            model_name=model_name, 
            temperature=0.7,
            response_format={'type': 'json_object'} 
        )

        # 2. 使用 PydanticOutputParser 来构建一个包含格式指令的链
        parser = PydanticOutputParser(pydantic_object=StructuredReport)
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", report_prompts.SYSTEM_INSTRUCTION),
            ("human", report_prompts.FINAL_REPORT_PROMPT_TEMPLATE + "\n\n{format_instructions}")
        ])
        chain = prompt_template | llm | parser

        # 3. 异步调用链
        response_dict = await chain.ainvoke({
            "topic": topic, "context": context,
            "formatting_instructions": formatting_instructions,
            "format_instructions": parser.get_format_instructions(),
        })
        response = StructuredReport.model_validate(response_dict)

    else:
        # **情况B：对于其他模型（如Gemini），继续使用LangChain的
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
    # --- ^^^^ 修改结束 ^^^^ ---

    print("最终报告已生成。")
    return {"final_report": response}

# --- 组装图 ---

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