from sqlalchemy import Column, Integer, String, DateTime
from .connection import Base
import datetime

class DbReport(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    theme = Column(String, index=True)
    original_topic = Column(String)
    model_name = Column(String)
    saved_at = Column(DateTime, default=datetime.datetime.utcnow)
    file_path = Column(String, unique=True)