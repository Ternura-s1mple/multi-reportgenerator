# backend/schemas/report_schemas.py
from pydantic import BaseModel, Field
from typing import List
import datetime

# 定义报告中一个章节的结构
class ReportSection(BaseModel):
    section_title: str = Field(..., description="本章节的标题")
    section_content: str = Field(..., description="本章节的详细内容，应为一段完整的文本。")

# 定义AI必须返回的最终报告结构
class StructuredReport(BaseModel):
    title: str = Field(..., description="整份报告的主标题")
    introduction: str = Field(..., description="报告的引言部分，对报告进行简要概述。")
    sections: List[ReportSection] = Field(..., description="报告的主体部分，由多个章节构成。")
    conclusion: str = Field(..., description="报告的结论部分。")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str    

class SaveRequest(BaseModel):
    topic: str
    model_name: str
    content: str

class ReportMetadata(BaseModel):
    id: int
    theme: str
    original_topic: str
    model_name: str
    saved_at: datetime.datetime

    class Config:
        orm_mode = True


class TopicRequest(BaseModel):
    topic: str