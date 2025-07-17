# backend/services/report_graph.py

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
import chromadb
import asyncio
from sentence_transformers import SentenceTransformer

from backend.services.graph_state import GraphState
from backend.services.model_adapters import get_model_adapter
from backend.schemas.report_schemas import StructuredReport
from backend.prompts import report_prompts
from backend.config.config import BASE_DIR, settings



# --- 定义图的节点 ---

async def expand_topic_node(state: GraphState) -> GraphState:
    """节点1: 将用户主题扩展为更具体的查询"""
    print(f"---[节点1: 主题扩展] | 收到状态键: {list(state.keys())} ---")
    topic = state['original_topic']
    model_name = state['model_name'] # 使用同一个模型进行扩展

    adapter = get_model_adapter(model_name)
    llm = adapter.create_chat_model(model_name=model_name, temperature=0.3)
    
    prompt = report_prompts.TOPIC_EXPANDER_PROMPT_TEMPLATE.format(topic=topic)
    response = await llm.ainvoke(prompt)
    
    queries = [q.strip() for q in response.content.split('\n') if q.strip()]
    print(f"扩展出的查询: {queries}")
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
    """
    节点3: 智能组装Prompt，结合RAG上下文和可选模板，生成最终报告
    """
    print(f"---[节点3: 最终报告生成] | 收到状态键: {list(state.keys())} ---")
    topic = state['original_topic']
    context = state['retrieved_context']
    model_name = state['model_name']
    template_content = state.get('template_content') # 安全地获取模板内容

    if template_content:
        print("    检测到用户模板，将用其作为格式指令。")
        formatting_instructions = template_content
    else:
        print("    未提供用户模板，使用默认的格式指令。")
        formatting_instructions = report_prompts.NO_TEMPLATE_INSTRUCTION

    adapter = get_model_adapter(model_name)
    llm = adapter.create_chat_model(model_name=model_name, temperature=0.5)
    structured_llm = llm.with_structured_output(StructuredReport)

    # 使用我们新的“终极”模板
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", report_prompts.SYSTEM_INSTRUCTION),
        ("human", report_prompts.FINAL_REPORT_PROMPT_TEMPLATE),
    ])

    # 填充所有需要的变量
    prompt_inputs = {
        "topic": topic,
        "context": context,
        "formatting_instructions": formatting_instructions
    }

    formatted_prompt = prompt_template.invoke(prompt_inputs)

    response = await structured_llm.ainvoke(formatted_prompt)
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