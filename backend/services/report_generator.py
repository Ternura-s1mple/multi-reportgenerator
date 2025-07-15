# backend/services/report_generator.py
from langchain_core.prompts import ChatPromptTemplate
from backend.prompts import report_prompts
from backend.services.model_adapters import get_model_adapter
from backend.schemas.report_schemas import StructuredReport
import json
import asyncio 

async def generate_structured_report(topic: str, model_name: str) -> StructuredReport:
    """
    根据主题和模型名称，生成结构化的报告。
    """
    print(f"开始使用模型 {model_name} 为主题 '{topic}' 生成结构化报告...")

    # 1. 获取模型适配器
    adapter = get_model_adapter(model_name)

    # 2. 创建一个LangChain聊天模型实例
    llm = adapter.create_chat_model(model_name=model_name, temperature=0.5)

    # 3. 将模型与我们定义的Pydantic Schema绑定，强制其输出JSON
    structured_llm = llm.with_structured_output(StructuredReport)

    # 4. 创建提示词模板
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", report_prompts.SYSTEM_INSTRUCTION),
        ("human", report_prompts.USER_PROMPT_TEMPLATE),
    ])
    
    # 5. 格式化并填充提示词
    formatted_prompt = prompt_template.invoke({"topic": topic})

    # 6. 调用模型并获取结构化结果
    try:
        result = await structured_llm.ainvoke(formatted_prompt)
        print(f"✅ 模型 {model_name} 成功生成报告。")
        return result
    except Exception as e:
        print(f"❌ 模型 {model_name} 生成报告失败: {e}")
        # 在失败时可以返回一个默认的错误报告结构
        return StructuredReport(
            title=f"报告生成失败: {topic}",
            introduction=f"尝试使用模型 {model_name} 生成报告时出现错误。",
            sections=[],
            conclusion=f"错误详情: {e}"
        )

# (辅助函数) 将结构化报告转换为Markdown
def convert_report_to_markdown(report: StructuredReport) -> str:
    md = f"# {report.title}\n\n"
    md += f"## 引言\n{report.introduction}\n\n"
    for section in report.sections:
        md += f"## {section.section_title}\n{section.section_content}\n\n"
    md += f"## 结论\n{report.conclusion}\n"
    return md

# backend/services/report_generator.py (在末尾添加)

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