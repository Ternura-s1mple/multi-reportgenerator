# backend/api/routes.py (最终完整版)

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.config.config import BASE_DIR
from backend.services.model_adapters import resolve_model_alias 
import asyncio
import os
import datetime

# 导入我们重构后的模块
from backend.services.report_generator import (
    generate_structured_report, 
    convert_report_to_markdown,
    generate_chat_stream
)
from backend.schemas import report_schemas
from backend.config.config import settings
from backend.database import models
from backend.database.connection import SessionLocal

# 数据库会话依赖 (从旧的main.py迁移过来)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter()

# --- 报告生成与对话相关端点 (这部分您已拥有) ---

@router.post("/api/reports/generate-mixed")
async def generate_mixed_reports(request: dict, db: Session = Depends(get_db)):
    topic = request.get("topic")
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required.")

    tasks = [
        generate_structured_report(topic, model_name) 
        for model_name in settings.MIXED_MODE_MODELS
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    final_reports = []
    # 注意：这里我们使用了新的向量存储逻辑，所以需要chroma_client和sentence_model
    # 您需要在您的 main.py 中将它们作为全局变量，或者通过更高级的依赖注入方式传入
    # 为简化，我们暂时假设可以从某处获取它们，或者在保存时再处理向量
    for result, model_name in zip(results, settings.MIXED_MODE_MODELS):
        if isinstance(result, report_schemas.StructuredReport):
            final_reports.append({
                "model_name": model_name,
                "content": convert_report_to_markdown(result)
            })
        else:
            print(f"❌ 模型 {model_name} 生成报告失败: {result}")
            final_reports.append({
                "model_name": model_name,
                "content": f"# 报告生成失败\n\n**错误详情:**\n```\n{result}\n```"
            })

    return {"reports": final_reports}


@router.post("/api/chat/completions")
async def chat_completions(request: report_schemas.ChatRequest):
    actual_model_name = resolve_model_alias(request.model)
    if not actual_model_name:
        async def error_stream():
            yield f"错误：未知的模型简称 '{request.model}'。"
        return StreamingResponse(error_stream(), media_type="text/event-stream")
    
    stream_generator = generate_chat_stream(
        messages=request.dict()['messages'], 
        model_name=actual_model_name
    )
    async def event_stream():
        async for chunk in stream_generator:
            yield chunk
    return StreamingResponse(event_stream(), media_type="text/event-stream")



@router.post("/api/save-report")
def save_report(request: report_schemas.SaveRequest, db: Session = Depends(get_db)):
    # 注意：这里的 SaveRequest 需要在 report_schemas.py 中定义
    print("\n" + "-"*50)
    print(f"收到保存请求: 模型='{request.model_name}'")

    theme = request.topic[:20].strip() # 稍微加长主题长度
    storage_dir = BASE_DIR / "storage" / theme
    os.makedirs(storage_dir, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    file_path = os.path.join(storage_dir, f"{request.model_name.replace(':', '-')}_{timestamp}.md")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(request.content)
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

    try:
        print("正在为新报告创建向量...")
        sentence_model = request.app.state.sentence_model
        collection = request.app.state.collection
        embedding = sentence_model.encode(request_data.topic).tolist()
        collection.add(
            embeddings=[embedding],
            metadatas=[{"theme": db_report.theme, "model_name": request_data.model_name}],
            ids=[str(db_report.id)]
        )
        print(f"向量已存入ChromaDB，ID: {db_report.id}")
    except Exception as e:
        print(f"❌ 存入向量数据库时发生错误: {e}")

    print("-"*50 + "\n")
    return {"message": "报告保存成功", "id": db_report.id, "path": file_path}


@router.get("/api/themes", response_model=list[str])
def get_themes(db: Session = Depends(get_db)):
    print("收到请求: 获取所有主题列表。")
    themes = db.query(models.DbReport.theme).distinct().all()
    return [theme[0] for theme in themes]


@router.get("/api/reports/{theme_name}", response_model=list[report_schemas.ReportMetadata])
def get_reports_by_theme(theme_name: str, db: Session = Depends(get_db)):
    print(f"收到请求: 获取主题 '{theme_name}' 下的报告列表。")
    reports = db.query(models.DbReport).filter(models.DbReport.theme == theme_name).order_by(models.DbReport.saved_at.desc()).all()
    return reports


@router.get("/api/report-content/{report_id}")
def get_report_content(report_id: int, db: Session = Depends(get_db)):
    print(f"收到请求: 获取报告ID {report_id} 的内容。")
    report = db.query(models.DbReport).filter(models.DbReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        with open(report.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Report file not found on disk at {report.file_path}")
    

@router.post("/api/find-similar", response_model=list[report_schemas.ReportMetadata])
def find_similar_reports(request_data: report_schemas.TopicRequest, request: Request, db: Session = Depends(get_db)):
    """根据主题查找相似的历史报告"""
    print(f"收到相似度搜索请求，主题: '{request_data.topic}'")
    collection = request.app.state.collection
    if collection.count() == 0:
        print("向量数据库为空，无需搜索。")
        return []

    sentence_model = request.app.state.sentence_model
    embedding = sentence_model.encode(request_data.topic).tolist()

    results = collection.query(query_embeddings=[embedding], n_results=3)

    if not results['ids'][0]:
        return []

    similar_ids = [int(id_str) for id_str in results['ids'][0]]
    print(f"找到相似报告ID: {similar_ids}")

    similar_reports = db.query(models.DbReport).filter(models.DbReport.id.in_(similar_ids)).all()
    return similar_reports    