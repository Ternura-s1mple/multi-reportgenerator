# backend/llm_services.py

import os
from openai import AsyncOpenAI
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# OpenAI 客户端初始化
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 配置 Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


async def generate_with_openai(model_name: str, topic: str):
    # 新增调试信息: 打印开始调用的信息
    print(f"🚀 [OpenAI] 开始调用模型: {model_name}...")
    try:
        prompt = f"你是一位资深的行业分析师。请根据以下主题，生成一份结构清晰、内容详尽的Markdown格式分析报告。主题：'{topic}'"
        response = await openai_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        # 新增调试信息: 打印成功信息
        print(f"✅ [OpenAI] 模型 {model_name} 调用成功。")
        return {"model_name": f"OpenAI-{model_name}", "content": content}
    except Exception as e:
        # 新增调试信息: 打印失败信息
        print(f"❌ [OpenAI] 模型 {model_name} 调用失败: {e}")
        return {"model_name": f"OpenAI-{model_name}", "content": f"调用失败: {e}"}


async def generate_with_gemini(model_name: str, topic: str):
    # 新增调试信息: 打印开始调用的信息
    print(f"🚀 [Gemini] 开始调用模型: {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"你是一位资深的行业分析师。请根据以下主题，生成一份结构清晰、内容详尽的Markdown格式分析报告。主题：'{topic}'"
        response = await model.generate_content_async(prompt)
        content = response.text
        # 新增调试信息: 打印成功信息
        print(f"✅ [Gemini] 模型 {model_name} 调用成功。")
        return {"model_name": f"Gemini-{model_name}", "content": content}
    except Exception as e:
        # 新增调试信息: 打印失败信息
        print(f"❌ [Gemini] 模型 {model_name} 调用失败: {e}")
        return {"model_name": f"Gemini-{model_name}", "content": f"调用失败: {e}"}


async def mock_llm_call(model_name: str, topic: str, delay: float = 1):
    print(f"🚀 [Mock] 开始调用模型: {model_name}...")
    await asyncio.sleep(delay)
    print(f"✅ [Mock] 模型 {model_name} 调用完成。")
    return {
        "model_name": model_name,
        "content": f"# {topic} - 由 {model_name} (模拟) 生成\n\n这是一个模拟报告，用于测试和展示。"
    }