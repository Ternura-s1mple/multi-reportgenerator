# backend/services/report_generator.py
from langchain_core.prompts import ChatPromptTemplate
from backend.prompts import report_prompts
from backend.services.model_adapters import get_model_adapter
from backend.schemas.report_schemas import StructuredReport
import json
import asyncio 

async def generate_structured_report(topic: str, model_name: str, template_content: str = "") -> StructuredReport:
    """
    根据主题、模型名称以及可选的模板内容，异步生成结构化的报告。
    """
    print(f"--> [开始] 使用模型 {model_name} 为主题 '{topic}' 生成报告...")
    print(f"    模板内容长度: {len(template_content)}字")

    adapter = get_model_adapter(model_name)
    llm = adapter.create_chat_model(model_name=model_name, temperature=0.5)
    structured_llm = llm.with_structured_output(StructuredReport)
    
    # 根据有无模板内容，选择不同的提示词
    if template_content:
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", report_prompts.SYSTEM_INSTRUCTION),
            ("human", report_prompts.TEMPLATE_BASED_REPORT_PROMPT),
        ])
        prompt_inputs = {"topic": topic, "template_content": template_content}
    else:
        # 回退到旧的、无模板的提示词
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", report_prompts.SYSTEM_INSTRUCTION),
            ("human", report_prompts.USER_PROMPT_TEMPLATE),
        ])
        prompt_inputs = {"topic": topic}
    
    formatted_prompt = prompt_template.invoke(prompt_inputs)
    
    result = await structured_llm.ainvoke(formatted_prompt)
    print(f"--> [成功] 模型 {model_name} 已生成报告。")
    return result

# (辅助函数) 将结构化报告转换为Markdown
def convert_report_to_markdown(report: StructuredReport) -> str:
    md = f"# {report.title}\n\n"
    md += f"## 引言\n{report.introduction}\n\n"
    for section in report.sections:
        md += f"## {section.section_title}\n{section.section_content}\n\n"
    md += f"## 结论\n{report.conclusion}\n"
    return md


async def generate_chat_stream(messages: list, model_name: str):
    """
    根据对话历史和模型名称，以流式方式生成响应。
    """
    print(f"开始为对话生成流式响应，模型: {model_name}")
    try:
        adapter = get_model_adapter(model_name)
        llm = adapter.create_chat_model(model_name=model_name, temperature=0.7)
        
        # LangChain 的流式调用方法 .astream()
        async for chunk in llm.astream(messages):
            yield chunk.content
            
    except Exception as e:
        print(f"❌ 流式对话生成失败: {e}")
        yield f"抱歉，处理您的请求时出现错误: {e}"