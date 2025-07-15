# backend/core/config.py
from typing import List # 确保导入 List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    
    GOOGLE_API_KEY: str
    OPENAI_API_KEY: str
    DEEPSEEK_API_KEY: str
    VLLM_QWEN_URL: str
    # vvvv 新增：定义混合模式要调用的模型列表 vvvv
    MIXED_MODE_MODELS: List[str] = [
        "gemini-2.5-flash",
        "deepseek-chat"
        # "Qwen/Qwen2.5-7B-Chat" # 如果您的本地模型在运行，可以取消这行注释
    ]
    # ^^^^                                       ^^^^

settings = Settings()


MODEL_MAPPING = {
    "gemini": "gemini-2.5-flash",
    "deepseek": "deepseek-chat",
    "qwen": "Qwen/Qwen2.5-7B-Chat"
}