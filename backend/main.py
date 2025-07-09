# backend/main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import datetime
import asyncio

# 导入 sentence-transformers 和 chromadb
from sentence_transformers import SentenceTransformer
import chromadb
# 导入我们创建的模块
#
# This is the new, corrected code
#
import models, schemas
from database import SessionLocal, engine
from llm_services import generate_with_openai, generate_with_gemini, mock_llm_call
from fastapi.middleware.cors import CORSMiddleware

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 全局加载模型和数据库 (在程序启动时执行一次) ---
print("正在加载句向量模型 (这可能需要一些时间)...")
sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
print("句向量模型加载完毕。")

print("正在初始化向量数据库...")
chroma_client = chromadb.Client()
# 使用 get_or_create_collection 避免重复创建
collection = chroma_client.get_or_create_collection(name="reports_collection")
print("向量数据库初始化完毕。")
# --- ---

# 数据库会话依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/generate-reports", response_model=schemas.GenerationResponse)
async def generate_reports(request: schemas.TopicRequest):
    topic = request.topic
    # 新增调试信息: 确认收到请求
    print("\n" + "="*50)
    print(f"收到新请求: 开始为主题 '{topic}' 生成报告...")
    print("="*50)

    tasks = [
        generate_with_gemini("gemini-1.5-flash-latest", topic),
        # generate_with_openai("gpt-4o-mini", topic), # 如果需要，可以取消这行的注释
        mock_llm_call("Claude 3.5 Sonnet (模拟)", topic, 1.5),
    ]
    
    # 新增调试信息: 确认开始并行调用
    print("...开始并行调用所有大模型...")
    results = await asyncio.gather(*tasks)
    # 新增调试信息: 确认所有调用已结束
    print("...所有模型调用已结束，正在整理结果...")
    
    successful_reports = [schemas.Report(**res) for res in results if res and res.get('content')]
    
    # 新增调试信息: 确认处理完成
    print("报告整理完毕，即将返回给前端。")
    print("="*50 + "\n")
    return schemas.GenerationResponse(reports=successful_reports)

@app.post("/api/save-report")
def save_report(request: schemas.SaveRequest, db: Session = Depends(get_db)):
    # 新增调试信息: 确认收到保存请求
    print("\n" + "-"*50)
    print(f"收到保存请求: 模型='{request.model_name}'")
    
    theme = request.topic[:15].strip()
    storage_dir = os.path.join("storage", theme)
    os.makedirs(storage_dir, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    file_path = os.path.join(storage_dir, f"{request.model_name.replace(':', '-')}_{timestamp}.md")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(request.content)

    # 新增调试信息: 确认文件已保存
    print(f"文件已成功保存至: {file_path}")

    db_report = models.DbReport(
        theme=theme,
        original_topic=request.topic,
        model_name=request.model_name,
        file_path=file_path,
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    print("报告元数据已存入SQL数据库。")

    # --- 新增：将主题向量化并存入ChromaDB ---
    print("正在为新报告创建向量...")
    embedding = sentence_model.encode(request.topic).tolist()
    collection.add(
        embeddings=[embedding],
        metadatas=[{"theme": theme, "model_name": request.model_name}],
        ids=[str(db_report.id)] # ID必须是字符串
    )
    print(f"向量已存入ChromaDB，ID: {db_report.id}")
    # --- ---

    print("-"*50 + "\n")
    return {"message": "报告保存成功", "id": db_report.id, "path": file_path}

@app.get("/")
def read_root():
    return {"message": "欢迎！"}

# backend/main.py (在文件末尾添加)

@app.get("/api/themes", response_model=list[str])
def get_themes(db: Session = Depends(get_db)):
    """获取所有不重复的主题列表"""
    print("收到请求: 获取所有主题列表。")
    themes = db.query(models.DbReport.theme).distinct().all()
    # The result is a list of tuples, e.g., [('Theme A',), ('Theme B',)], so we unpack it.
    return [theme[0] for theme in themes]

@app.get("/api/reports/{theme_name}", response_model=list[schemas.ReportMetadata])
def get_reports_by_theme(theme_name: str, db: Session = Depends(get_db)):
    """根据主题名称获取报告元数据列表"""
    print(f"收到请求: 获取主题 '{theme_name}' 下的报告列表。")
    reports = db.query(models.DbReport).filter(models.DbReport.theme == theme_name).order_by(models.DbReport.saved_at.desc()).all()
    return reports

@app.get("/api/report-content/{report_id}")
def get_report_content(report_id: int, db: Session = Depends(get_db)):
    """根据报告ID获取其Markdown文件内容"""
    print(f"收到请求: 获取报告ID {report_id} 的内容。")
    report = db.query(models.DbReport).filter(models.DbReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        with open(report.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report file not found on disk")

# 别忘了重启 uvicorn 服务来加载新代码
@app.post("/api/find-similar", response_model=list[schemas.ReportMetadata])
def find_similar_reports(request: schemas.TopicRequest, db: Session = Depends(get_db)):
    """根据主题查找相似的历史报告"""
    print(f"收到相似度搜索请求，主题: '{request.topic}'")
    if collection.count() == 0:
        print("向量数据库为空，无需搜索。")
        return []

    # 1. 将新主题转换为向量
    embedding = sentence_model.encode(request.topic).tolist()

    # 2. 在ChromaDB中查询
    results = collection.query(query_embeddings=[embedding], n_results=3)

    similar_ids = [int(id_str) for id_str in results['ids'][0]]
    print(f"找到相似报告ID: {similar_ids}")

    if not similar_ids:
        return []

    # 3. 从SQL数据库中获取这些ID的元数据
    similar_reports = db.query(models.DbReport).filter(models.DbReport.id.in_(similar_ids)).all()
    return similar_reports
