from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel

class CrawlerConfig(BaseModel):
    __tablename__ = 'crawler_configs'
    
    source_id = Column(String(36), ForeignKey('data_sources.id'), nullable=False)
    frequency = Column(String(20))  # 'daily' | 'hourly' | 'weekly'
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime)
    status = Column(String(20))  # 'enabled' | 'disabled'
    log_path = Column(String(255))
    
    # Relationships
    source = relationship('DataSource', back_populates='crawler_configs')
