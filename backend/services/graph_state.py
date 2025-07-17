from typing import List, TypedDict, Optional, Any
from backend.schemas.report_schemas import StructuredReport

class GraphState(TypedDict):
    original_topic: str          # 用户的原始主题
    expanded_queries: List[str]  # 节点1的输出：扩展后的查询列表
    retrieved_context: str       # 节点2的输出：检索到的上下文文本
    final_report: Optional[StructuredReport] # 节点3的输出：最终报告
    model_name: str              # 要使用的模型名称
    template_content: Optional[str]   #可选的模板内容
    sentence_model: Optional[Any]
    reports_collection: Optional[Any]
    knowledge_collection: Optional[Any]