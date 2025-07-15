# backend/services/model_adapters.py
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.config.config import settings, MODEL_MAPPING 

# 这是一个抽象基类或接口的概念，实际可省略
class ModelAdapter:
    def create_chat_model(self, model_name: str, temperature: float = 0.7):
        raise NotImplementedError

# 针对不同厂商模型的具体实现
class GeminiAdapter(ModelAdapter):
    def create_chat_model(self, model_name: str, temperature: float = 0.7):
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=temperature,
        )

class OpenAIAdapter(ModelAdapter):
    def create_chat_model(self, model_name: str, temperature: float = 0.7):
        return ChatOpenAI(
            model=model_name,
            api_key=settings.OPENAI_API_KEY,
            temperature=temperature
        )
        
class DeepSeekAdapter(ModelAdapter):
    def create_chat_model(self, model_name: str, temperature: float = 0.7):
        return ChatOpenAI(
            model=model_name,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",
            temperature=temperature
        )

# 工厂函数：根据模型名称返回对应的适配器实例
def get_model_adapter(model_name: str) -> ModelAdapter:
    if "gemini" in model_name:
        return GeminiAdapter()
    elif "deepseek" in model_name:
        return DeepSeekAdapter()
    # 更多模型可以在这里添加...
    else: # 默认为OpenAI兼容模型 (包括vLLM)
        return OpenAIAdapter()
    
def resolve_model_alias(alias: str) -> str | None:
    """
    根据前端传来的别名(alias)，查找真实的API模型名称。
    这是一个专门的服务函数，封装了映射逻辑。
    """
    return MODEL_MAPPING.get(alias)