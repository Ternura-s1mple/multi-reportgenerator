# backend/services/report_graph.py

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
import chromadb
from sentence_transformers import SentenceTransformer

from backend.services.graph_state import GraphState
from backend.services.model_adapters import get_model_adapter
from backend.schemas.report_schemas import StructuredReport
from backend.prompts import report_prompts
from backend.config.config import BASE_DIR, settings

# --- RAG 工具初始化 ---
KNOWLEDGE_COLLECTION_NAME = "local_knowledge_base" # <--- 指向新知识库集合
try:
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder=str(BASE_DIR / '.cache'))
    chroma_client = chromadb.Client()
    # 注意：这里我们只“获取”集合，因为数据注入是由 ingest.py 完成的
    knowledge_collection = chroma_client.get_collection(name=KNOWLEDGE_COLLECTION_NAME)
    print("RAG知识库集合加载成功。")
except Exception as e:
    print(f"初始化RAG知识库时出错: {e}. RAG检索功能将不可用。")
    knowledge_collection = None

# --- 定义图的节点 ---

def expand_topic_node(state: GraphState) -> GraphState:
    """节点1: 将用户主题扩展为更具体的查询"""
    print("---[节点1: 主题扩展]---")
    topic = state['original_topic']
    model_name = state['model_name'] # 使用同一个模型进行扩展

    adapter = get_model_adapter(model_name)
    llm = adapter.create_chat_model(model_name=model_name, temperature=0.3)
    
    prompt = report_prompts.TOPIC_EXPANDER_PROMPT_TEMPLATE.format(topic=topic)
    response = llm.invoke(prompt)
    
    queries = [q.strip() for q in response.content.split('\n') if q.strip()]
    print(f"扩展出的查询: {queries}")
    return {"expanded_queries": queries}


def retrieve_context_node(state: GraphState) -> GraphState:
    """节点2: 从本地知识库进行RAG检索"""
    print("---[节点2: 上下文检索 (从本地知识库)]---")
    if not knowledge_collection or not sentence_model:
        print("知识库未初始化，跳过检索。")
        return {"retrieved_context": "无相关知识库资料。"}

    queries = state['expanded_queries']
    print(f"正在使用查询进行检索: {queries}")
    embeddings = sentence_model.encode(queries).tolist()

    # vvvv 核心修改：从新的知识库集合中查询 vvvv
    results = knowledge_collection.query(
        query_embeddings=embeddings, 
        n_results=5 # 可以调整检索出的文档块数量
    )
    # ^^^^                               ^^^^

    context_list = results.get('documents', [[]])[0]
    context_str = "\n\n---\n\n".join(context_list)

    print(f"检索到的知识库上下文长度: {len(context_str)}字")
    return {"retrieved_context": context_str or "在本地知识库中未找到相关资料。"}


def generate_report_node(state: GraphState) -> GraphState:
    """节点3: 结合上下文和可选的模板，生成最终报告"""
    print("---[节点3: 最终报告生成]---")
    topic = state['original_topic']
    context = state['retrieved_context']
    model_name = state['model_name']
    template_content = state.get('template_content') # 安全地获取模板内容

    adapter = get_model_adapter(model_name)
    llm = adapter.create_chat_model(model_name=model_name, temperature=0.5)
    structured_llm = llm.with_structured_output(StructuredReport)

    # vvvv 核心修改：根据有无模板内容，选择并格式化不同的Prompt vvvv
    if template_content:
        print("    检测到模板内容，使用基于模板的提示词。")
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", report_prompts.SYSTEM_INSTRUCTION),
            ("human", report_prompts.TEMPLATE_BASED_REPORT_PROMPT),
        ])
        prompt_inputs = {"topic": topic, "template_content": template_content}
    else:
        print("    未提供模板，使用基于RAG上下文的提示词。")
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", report_prompts.SYSTEM_INSTRUCTION),
            ("human", report_prompts.RAG_REPORT_PROMPT_TEMPLATE),
        ])
        prompt_inputs = {"topic": topic, "context": context}
    # ^^^^ 修改结束 ^^^^

    formatted_prompt = prompt_template.invoke(prompt_inputs)

    response = structured_llm.invoke(formatted_prompt)
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