from sqlalchemy import Column, String, DateTime, Integer, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from datetime import datetime
from .base_model import BaseModel

class CrawlHistory(BaseModel):
    __tablename__ = 'crawl_histories'
    
    # Foreign Keys
    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'), nullable=False)
    
    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    
    # Scheduling
    last_run_at = Column(DateTime)  # When this crawl session actually ran
    next_run_at = Column(DateTime)  # When the next crawl is scheduled
    
    # Status
    status = Column(String(20), nullable=False, default='running')  # 'running', 'completed', 'failed', 'cancelled'
    
    # Statistics
    total_jobs_found = Column(Integer, default=0)
    jobs_created = Column(Integer, default=0)
    jobs_updated = Column(Integer, default=0)
    jobs_skipped = Column(Integer, default=0)
    jobs_failed = Column(Integer, default=0)
    
    # Error handling
    error_count = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Performance metrics
    pages_crawled = Column(Integer, default=0)
    avg_response_time_ms = Column(Float)
    
    # Metadata
    crawler_version = Column(String(50))
    user_agent = Column(String(200))
    
    # Relationships
    source = relationship('DataSource', back_populates='crawl_histories')
    
    def __repr__(self):
        return f"<CrawlHistory(id={self.id}, source_id={self.source_id}, status={self.status})>"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        total_processed = self.jobs_created + self.jobs_updated + self.jobs_failed
        if total_processed == 0:
            return 0.0
        return ((self.jobs_created + self.jobs_updated) / total_processed) * 100
    
    @property
    def is_running(self) -> bool:
        """Check if crawl is currently running"""
        return self.status == 'running'
    
    @property
    def is_completed(self) -> bool:
        """Check if crawl completed successfully"""
        return self.status == 'completed'
    
    @property
    def is_failed(self) -> bool:
        """Check if crawl failed"""
        return self.status == 'failed'