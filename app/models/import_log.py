from sqlalchemy import Column, String, DateTime, Text
from .base_model import BaseModel
from datetime import datetime

class MinioImportLog(BaseModel):
    __tablename__ = 'minio_import_logs'
    
    bucket_name = Column(String(100), nullable=False)
    object_name = Column(String(500), nullable=False)
    etag = Column(String(100))
    status = Column(String(20)) # 'success', 'failed'
    error_message = Column(Text)
    processed_at = Column(DateTime, default=datetime.utcnow)
