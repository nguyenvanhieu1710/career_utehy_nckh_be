from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel
from sqlalchemy.dialects.postgresql import UUID, JSONB

class CrawlerConfig(BaseModel):
    __tablename__ = 'crawler_configs'
    
    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'), nullable=False)
    frequency = Column(String(20))  # 'daily' | 'hourly' | 'weekly'
    status = Column(String(20))  # 'enabled' | 'disabled'
    cron_expression = Column(String(50))  # '0 * * * *'
    timezone = Column(String(50), default='UTC')  # Timezone for scheduling
    last_scheduled_at = Column(DateTime)  # Last time this job was scheduled    
    crawler_payload = Column(JSONB) # Contains user_name, web_name, steps, repeat, link_key, etc.
    
    # Relationships
    source = relationship('DataSource', back_populates='crawler_configs')
    
    @property
    def is_scheduled(self) -> bool:
        """Check if this config has active scheduling"""
        return self.status == 'enabled' and self.cron_expression is not None