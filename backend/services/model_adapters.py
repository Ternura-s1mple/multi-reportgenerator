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
    def create_chat_model(self, model_name: str, temperature: float = 0.7, **kwargs):
        return ChatOpenAI(
            model=model_name,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",
            temperature=temperature,
            model_kwargs=kwargs
        )
    
class QwenApiAdapter(ModelAdapter):
    def create_chat_model(self, model_name: str, temperature: float = 0.7, **kwargs):
        return ChatOpenAI(
            model=model_name,
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=temperature,
            model_kwargs=kwargs
        )
    
class VLLMAdapter(ModelAdapter):
    def create_chat_model(self, model_name: str, temperature: float = 0.7, **kwargs):
        return ChatOpenAI(
            model=model_name,
            api_key="EMPTY",  # vLLM通常不需要密钥
            base_url=settings.VLLM_QWEN_URL,
            temperature=temperature,
            model_kwargs=kwargs
        )

  

# 工厂函数：根据模型名称返回对应的适配器实例
def get_model_adapter(model_name: str) -> ModelAdapter:
    if model_name.startswith("gemini"):
        return GeminiAdapter()
    elif model_name.startswith("deepseek"):
        return DeepSeekAdapter()
    elif model_name in MODEL_MAPPING.values() and "qwen" in model_name.lower():
        if model_name == MODEL_MAPPING.get("qwen-api"):
             return QwenApiAdapter()
        else: # 认为是本地部署的Qwen
             return VLLMAdapter()
    else:
        # 可以保留一个通用的VLLM作为默认或抛出错误
        print(f"警告：未找到完全匹配的适配器，将使用通用的VLLM适配器。模型: {model_name}")
        return VLLMAdapter()
    
def resolve_model_alias(alias: str) -> str | None:
    """
    根据前端传来的别名(alias)，查找真实的API模型名称。
    专门的服务函数，封装了映射逻辑。
    """
    return MODEL_MAPPING.get(alias)