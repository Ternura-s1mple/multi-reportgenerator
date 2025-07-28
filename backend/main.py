# backend/main.py (恢复了全局模型加载)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

from backend.api.routes import router as api_router
from backend.database import models
from backend.database.connection import engine
from backend.config.config import BASE_DIR
from sentence_transformers import SentenceTransformer, CrossEncoder
# --- 在应用启动时执行 ---
models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Multi-Model Report Generator API")

@app.on_event("startup")
def startup_event():
    models_dir = BASE_DIR.parent / "models"
    embedding_model_path = models_dir / "bge-base-zh-v1.5"
    reranker_model_path = models_dir / "bge-reranker-large"

    print(f"正在从本地路径加载 BGE 嵌入模型: {embedding_model_path}")
    app.state.sentence_model = SentenceTransformer(
        str(embedding_model_path), 
        cache_folder=str(BASE_DIR / '.cache')
    )
    print("BGE 嵌入模型加载完毕。")

    print(f"正在从本地路径加载 BGE Reranker 模型: {reranker_model_path}")
    app.state.reranker_model = CrossEncoder(
        str(reranker_model_path),
        cache_folder=str(BASE_DIR / '.cache')
    )
    print("BGE Reranker 模型加载完毕。")
    # --- ^^^^                      ^^^^ ---

    print("正在初始化持久化的向量数据库...")
    db_path = str(BASE_DIR / ".chroma_db")
    chroma_client = chromadb.PersistentClient(path=db_path)

    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=str(embedding_model_path) # ChromaDB也使用本地路径
    )

    app.state.reports_collection = chroma_client.get_or_create_collection(
        name="reports_collection",
        embedding_function=sentence_transformer_ef
    )
    app.state.knowledge_collection = chroma_client.get_or_create_collection(
        name="local_knowledge_base",
        embedding_function=sentence_transformer_ef
    )
    print("向量数据库初始化完毕，并已配置好本地向量模型。")

# --- 中间件 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "欢迎使用新架构的报告生成器API！"}