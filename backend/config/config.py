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
    QWEN_API_KEY: str

    MIXED_MODE_MODELS: List[str] = [
        # "gemini-2.5-flash",
        "deepseek-chat",
        "/data2/models/Qwen2.5-72B-Instruct",
        "qwen-long"
    ]


settings = Settings()


MODEL_MAPPING = {
    # "gemini": "gemini-2.5-flash",
    "deepseek": "deepseek-chat",
    "qwen-local": "/data2/models/Qwen2.5-72B-Instruct",
    "qwen-api": "qwen-long"
}