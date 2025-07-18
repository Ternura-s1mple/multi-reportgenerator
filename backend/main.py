# backend/main.py (恢复了全局模型加载)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
import chromadb

from backend.api.routes import router as api_router
from backend.database import models
from backend.database.connection import engine
from backend.config.config import BASE_DIR
# --- 在应用启动时执行 ---
models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Multi-Model Report Generator API")

@app.on_event("startup")
def startup_event():
    print("正在加载句向量模型...")
    app.state.sentence_model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder=str(BASE_DIR / '.cache'))
    print("句向量模型加载完毕。")
    print("正在初始化持久化的向量数据库...")
    db_path = str(BASE_DIR / ".chroma_db")
    print(f"向量数据库将被保存在: {db_path}")
    

    chroma_client = chromadb.PersistentClient(path=db_path)
    
    # 将两个集合都加载到 app.state 中
    # get_or_create_collection 会在集合不存在时创建它
    app.state.reports_collection = chroma_client.get_or_create_collection(name="reports_collection")
    app.state.knowledge_collection = chroma_client.get_or_create_collection(name="local_knowledge_base")
    print("向量数据库初始化完毕。")

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