from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel

class DataSource(BaseModel):
    __tablename__ = 'data_sources'
    
    name = Column(String(100), nullable=False)
    base_url = Column(String(255))
    status = Column(String(20))  # 'active' | 'inactive'
    last_crawled_at = Column(DateTime)
    
    # Relationships
    jobs = relationship('Job', back_populates='source')
    crawler_configs = relationship('CrawlerConfig', back_populates='source')
