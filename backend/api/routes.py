# backend/api/routes.py (最终完整版)

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.config.config import BASE_DIR
from backend.services.model_adapters import resolve_model_alias 
import asyncio
import os
import datetime
from pathlib import Path
import numpy as np

# 导入我们重构后的模块
from backend.services.report_generator import (
    generate_structured_report, 
    convert_report_to_markdown,
    generate_chat_stream
)
from backend.services.report_graph import graph as report_graph
from backend.schemas import report_schemas
from backend.config.config import settings
from backend.database import models
from backend.database.connection import SessionLocal
from backend.utils.file_parser import parse_docx_template

# 数据库会话依赖 
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter()


@router.post("/api/reports/generate-mixed")
async def generate_mixed_reports(request: Request, db: Session = Depends(get_db)):
    """
    混合模式 (无模板): 并行运行LangGraph工作流。
    """
    try:
        body = await request.json()
        topic = body.get("topic")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")
    
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required in JSON body.")

    tasks = []
    for model_name in settings.MIXED_MODE_MODELS:
        initial_state = {
            "original_topic": topic,
            "model_name": model_name,
            "template_content": None,
            "sentence_model": request.app.state.sentence_model,
            "reranker_model": request.app.state.reranker_model,
            "reports_collection": request.app.state.reports_collection,
            "knowledge_collection": request.app.state.knowledge_collection,
        }
        print(f"为模型 {model_name} 创建无模板任务，状态键: {list(initial_state.keys())}")
        tasks.append(report_graph.ainvoke(initial_state))
    
    final_states = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_reports = []
    for result_state, model_name in zip(final_states, settings.MIXED_MODE_MODELS):
         if isinstance(result_state, dict) and result_state.get("final_report"):
            report_obj = result_state["final_report"]
            final_reports.append({
                "model_name": model_name,
                "content": convert_report_to_markdown(report_obj)
            })
         else:
            print(f"❌ 模型 {model_name} 的工作流执行失败: {result_state}")
            final_reports.append({
                "model_name": model_name,
                "content": f"# 工作流执行失败\n\n**错误详情:**\n```\n{result_state}\n```"
            })
    return {"reports": final_reports}


@router.post("/api/reports/generate-from-template")
async def generate_from_template(
    request: Request, #注入Request对象以访问全局app.state
    db: Session = Depends(get_db), #注入DB会话
    topic: str = Form(...),
    template_file: UploadFile = File(...)
):
    """
    混合模式 (有模板): 解析模板并并行运行LangGraph工作流。
    """
    if not template_file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="模板文件必须是 .docx 格式。")

    template_content = await parse_docx_template(template_file)
    if not template_content:
        raise HTTPException(status_code=400, detail="无法解析模板文件或文件为空。")
    
    # 统一调用图，传入解析后的 template_content
    tasks = []
    for model_name in settings.MIXED_MODE_MODELS:
        initial_state = {
            "original_topic": topic,
            "model_name": model_name,
            "template_content": template_content, # 传入模板内容
            "sentence_model": request.app.state.sentence_model,
            "reranker_model": request.app.state.reranker_model,
            "reports_collection": request.app.state.reports_collection,
            "knowledge_collection": request.app.state.knowledge_collection
        }
        tasks.append(report_graph.ainvoke(initial_state))

    # 并行执行和后续处理逻辑与上面完全相同
    final_states = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_reports = []
    for result_state, model_name in zip(final_states, settings.MIXED_MODE_MODELS):
        if isinstance(result_state, dict) and result_state.get("final_report"):
            report_obj = result_state["final_report"]
            final_reports.append({
                "model_name": model_name,
                "content": convert_report_to_markdown(report_obj)
            })
        else:
            print(f"❌ 模型 {model_name} 的工作流执行失败: {result_state}")
            final_reports.append({
                "model_name": model_name,
                "content": f"# 工作流执行失败\n\n**错误详情:**\n```\n{result_state}\n```"
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
def save_report(request_data: report_schemas.SaveRequest, request: Request, db: Session = Depends(get_db)):
   

    print("\n" + "-"*50)
    print(f"收到保存请求: 模型='{request_data.model_name}'") # 使用 request_data

    theme = request_data.topic[:20].strip()
    storage_dir = BASE_DIR / "storage" / theme # 使用BASE_DIR
    os.makedirs(storage_dir, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    file_path = storage_dir / f"{request_data.model_name.replace(':', '-')}_{timestamp}.md"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(request_data.content)
    print(f"文件已成功保存至: {file_path}")

    db_report = models.DbReport(
        theme=theme,
        original_topic=request_data.topic,
        model_name=request_data.model_name,
        file_path=str(file_path), # 确保路径是字符串
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    print("报告元数据已存入SQL数据库。")

    try:
        print("正在为新报告创建向量...")
        sentence_model = request.app.state.sentence_model
        collection = request.app.state.reports_collection
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
    return {"message": "报告保存成功", "id": db_report.id, "path": str(file_path)}


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
    """使用 BGE Bi-Encoder + Cross-Encoder Reranker 进行两阶段相似度检索"""
    print(f"收到BGE两阶段搜索请求，主题: '{request_data.topic}'")
    collection = request.app.state.reports_collection
    if collection.count() == 0:
        return []
    print("--- [阶段1: 召回] ---")
    # 从 app.state 获取 BGE 嵌入模型
    sentence_model = request.app.state.sentence_model
    query_embedding = sentence_model.encode(request_data.topic).tolist()

    # 从向量数据库中召回一批可能相关的候选文档
    recall_results = collection.query(query_embeddings=[query_embedding], n_results=10)
    if not recall_results or not recall_results['ids'][0]:
        return []

    recall_ids = [int(id_str) for id_str in recall_results['ids'][0]]

    # 从SQL数据库中获取这些候选文档的原始内容
    recalled_reports = db.query(models.DbReport).filter(models.DbReport.id.in_(recall_ids)).all()

    print("--- [阶段2: 精排] ---")
    # 从 app.state 获取 BGE Reranker 模型
    reranker_model = request.app.state.reranker_model

    # 准备 Cross-Encoder 的输入：[(查询, 文档1), (查询, 文档2), ...]
    pairs = [[request_data.topic, report.original_topic] for report in recalled_reports]

    if not pairs:
        return []

    print(f"    正在为 {len(pairs)} 个候选文档计算相关度分数...")
    scores = reranker_model.predict(pairs)
    print("    分数计算完成。")

    # 将分数与报告对象关联，并按分数从高到低排序
    scored_reports = sorted(zip(scores, recalled_reports), key=lambda x: x[0], reverse=True)

    # 应用相似度阈值并提取最终ID
    truly_similar_reports = []
    RERANK_THRESHOLD = 0.1 # Reranker的分数阈值通常和向量距离不同

    print("--- [精排结果过滤] ---")
    for score, report in scored_reports:
        if score > RERANK_THRESHOLD:
            print(f"    - ID {report.id} (分数: {score:.4f}) - 相关，保留。")
            truly_similar_reports.append(report)
        else:
            print(f"    - ID {report.id} (分数: {score:.4f}) - 不够相关，忽略。")

    if not truly_similar_reports:
        print("精排后未找到足够相关的报告。")
        return []

    print(f"找到真正相似的报告: {[r.id for r in truly_similar_reports]}")
    return truly_similar_reports


# 删除单个报告记录及其关联文件和向量
@router.delete("/api/report/{report_id}", status_code=204)
def delete_report(report_id: int, request: Request, db: Session = Depends(get_db)):
    print(f"收到删除请求: 报告ID {report_id}")
    report = db.query(models.DbReport).filter(models.DbReport.id == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="报告记录未找到")

    # 1. 从磁盘删除 .md 文件
    try:
        file_path = Path(report.file_path)
        # 兼容旧的相对路径和新的绝对路径
        if not file_path.is_absolute():
            file_path = Path(settings.BASE_DIR) / file_path

        if file_path.exists():
            os.remove(file_path)
            print(f"✅ 已从磁盘删除文件: {file_path}")
        else:
            print(f"⚠️ 磁盘上未找到文件，跳过删除: {file_path}")
    except Exception as e:
        print(f"❌ 删除磁盘文件时出错: {e}")
        # 即使文件删除失败，也继续删除数据库记录

    # 2. 从向量数据库删除向量
    try:
        collection = request.app.state.reports_collection
        collection.delete(ids=[str(report_id)])
        print(f"已从向量数据库删除ID: {report_id}")
    except Exception as e:
        print(f"从向量数据库删除时出错: {e}")

    # 3. 从SQL数据库删除元数据记录
    db.delete(report)
    db.commit()
    print(f"已从SQL数据库删除记录: {report_id}")

    return # 返回 204 No Content

# 删除一个主题下的所有报告
@router.delete("/api/theme/{theme_name}", status_code=204)
def delete_theme(theme_name: str, request: Request, db: Session = Depends(get_db)):
    """删除一个主题下的所有报告"""
    print(f"收到删除请求: 主题 '{theme_name}'")
    reports_to_delete = db.query(models.DbReport).filter(models.DbReport.theme == theme_name).all()

    if not reports_to_delete:
        raise HTTPException(status_code=404, detail="该主题下没有任何报告")

    report_ids_to_delete = [str(report.id) for report in reports_to_delete]

    # 1. 批量从磁盘删除文件
    for report in reports_to_delete:
        try:
            file_path = Path(report.file_path)
            if not file_path.is_absolute():
                file_path = Path(settings.BASE_DIR) / file_path

            if file_path.exists():
                os.remove(file_path)
        except Exception as e:
            print(f"❌ 删除文件 {report.file_path} 时出错: {e}")
    print("磁盘文件删除操作完成。")

    # 2. 批量从向量数据库删除
    try:
        collection = request.app.state.reports_collection
        collection.delete(ids=report_ids_to_delete)
        print(f"已从向量数据库删除IDs: {report_ids_to_delete}")
    except Exception as e:
        print(f"从向量数据库批量删除时出错: {e}")

    # 3. 批量从SQL数据库删除
    db.query(models.DbReport).filter(models.DbReport.theme == theme_name).delete(synchronize_session=False)
    db.commit()
    print(f"已从SQL数据库删除主题 '{theme_name}' 的所有记录。")

    return