from pydantic import BaseModel
import datetime

class TopicRequest(BaseModel):
    topic: str

class Report(BaseModel):
    model_name: str
    content: str

class GenerationResponse(BaseModel):
    reports: list[Report]

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
        orm_mode = True # 允许从ORM对象转换